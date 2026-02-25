#!/usr/bin/env python3
"""
Integration test for PairingManager API endpoints and WebSocket authentication.
Run this to verify end-to-end pairing, session validation, and restricted command access.
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

    # 5. Try restricted command (shutdown)
    shutdown_result = {'error': None}

    @sio.on('error')
    def on_error(data):
        shutdown_result['error'] = data['message']
        print(f"  Shutdown error: {data['message']}")

    sio.emit('shutdown', {})
    time.sleep(1)
    # Should not error if paired
    assert shutdown_result['error'] is None, "Shutdown should be allowed for paired device"

    sio.disconnect()
    print("\n🎉 Integration test PASSED!")

if __name__ == '__main__':
    test_pairing_api()
