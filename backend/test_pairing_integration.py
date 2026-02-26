#!/usr/bin/env python3
"""
Integration test for PairingManager API endpoints and WebSocket authentication.
Run this to verify end-to-end pairing, session validation, and restricted command access.

WARNING: This test is SAFE to run — it does NOT perform any real shutdown/reboot.
The shutdown test only verifies the API accepts the request, it does NOT execute it.
"""

import requests
import sys
import os
import time
import socketio

API_URL = 'http://localhost:5000'
WS_URL = 'ws://localhost:5000/socket.io/'


def test_pairing_api():
    print("=" * 60)
    print("Integration Test: Pairing API & WebSocket")
    print("=" * 60)

    # 1. Generate pairing token (simulate touchscreen)
    resp = requests.post(f'{API_URL}/api/pair/generate')
    assert resp.status_code == 200, "Failed to generate pairing token"
    data = resp.json()
    token = data['token']
    print(f"  Generated token: {token}")

    # 2. Validate pairing token (simulate phone)
    device_info = {
        'token': token,
        'device_id': 'integration-device-1',
        'device_name': 'Integration Phone',
    }
    resp = requests.post(f'{API_URL}/api/pair/validate', json=device_info)
    assert resp.status_code == 200, "Failed to validate pairing token"
    result = resp.json()
    assert result['success'], "Pairing should succeed"
    session_token = result['session_token']
    print(f"  Session token: {session_token[:20]}...")

    # 3. Check pairing status
    resp = requests.get(f'{API_URL}/api/pair/status', headers={'X-Session-Token': session_token})
    assert resp.status_code == 200, "Failed to get pairing status"
    status = resp.json()
    assert status['is_paired'], "Should be paired"
    print(f"  Paired device: {status['paired_device']}")

    # 4. WebSocket authentication
    sio = socketio.Client()
    auth_success = False
    auth_failed = False

    @sio.on('auth_success')
    def on_auth_success(data):
        nonlocal auth_success
        auth_success = True
        print("  WebSocket authenticated!")

    @sio.on('auth_failed')
    def on_auth_failed(data):
        nonlocal auth_failed
        auth_failed = True
        print("  WebSocket authentication failed!")

    sio.connect(API_URL)
    sio.emit('authenticate', {'session_token': session_token})
    time.sleep(1)
    assert auth_success, "WebSocket authentication should succeed"

    # 5. Verify paired device can access protected API routes (without actually shutting down)
    # NOTE: We test auth on config endpoint, NOT shutdown — to avoid accidental RPi shutdown
    print("  Testing paired device access on protected route (GET /api/config)...")
    resp = requests.get(f'{API_URL}/api/config', headers={'X-Session-Token': session_token})
    assert resp.status_code == 200, "Paired device should access config"
    print("  Paired device can access protected routes")

    # 6. Verify unpaired device CANNOT access protected routes
    resp = requests.post(f'{API_URL}/api/shutdown', headers={'X-Session-Token': 'invalid-token'})
    assert resp.status_code == 401, "Invalid token should be rejected"
    print("  Invalid token rejected (401)")

    sio.disconnect()
    print("\nIntegration test PASSED!")

if __name__ == '__main__':
    test_pairing_api()
