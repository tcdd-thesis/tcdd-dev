#!/usr/bin/env python3
"""
Test script for PairingManager (Phase 1)
Run this on the Raspberry Pi to verify pairing logic works correctly.

Usage:
    cd /path/to/tcdd-dev
    python backend/test_pairing.py
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from pairing import PairingManager

def test_pairing_manager():
    """Run all tests for PairingManager"""
    
    print("=" * 60)
    print("Testing PairingManager (Phase 1)")
    print("=" * 60)
    
    # Use a test directory to avoid affecting real data
    test_dir = 'data/test_pairing'
    os.makedirs(test_dir, exist_ok=True)
    
    # Create a fresh instance
    pm = PairingManager(data_dir=test_dir)
    
    # Test 1: Initial state
    print("\n[Test 1] Initial State")
    print(f"  Is paired: {pm.is_paired()}")
    print(f"  Pending token: {pm.get_pending_token()}")
    assert pm.is_paired() == False, "Should not be paired initially"
    assert pm.get_pending_token() == None, "Should have no pending token"
    print("  PASSED")
    
    # Test 2: Generate token
    print("\n[Test 2] Generate Pairing Token")
    token = pm.generate_pairing_token()
    print(f"  Generated token: {token}")
    print(f"  Token length: {len(token)}")
    assert len(token) == 8, "Token should be 8 characters"
    assert pm.get_pending_token() == token, "Pending token should match"
    print("  PASSED")
    
    # Test 3: Invalid token validation
    print("\n[Test 3] Invalid Token Validation")
    result = pm.validate_and_pair("WRONGTOK", {
        'device_id': 'test-device-1',
        'device_name': 'Test Phone',
        'user_agent': 'Test/1.0'
    })
    print(f"  Result: {result}")
    assert result['success'] == False, "Should fail with wrong token"
    assert pm.is_paired() == False, "Should still not be paired"
    print("  PASSED")
    
    # Test 4: Valid token validation
    print("\n[Test 4] Valid Token Validation")
    result = pm.validate_and_pair(token, {
        'device_id': 'test-device-1',
        'device_name': 'Test Phone',
        'user_agent': 'Mozilla/5.0 (iPhone; Test)'
    })
    print(f"  Result: success={result['success']}, message={result['message']}")
    assert result['success'] == True, "Should succeed with correct token"
    assert 'session_token' in result, "Should return session token"
    assert pm.is_paired() == True, "Should be paired now"
    assert pm.get_pending_token() == None, "Pending token should be cleared"
    
    session_token = result['session_token']
    print(f"  Session token: {session_token[:20]}...")
    print("  PASSED")
    
    # Test 5: Session validation
    print("\n[Test 5] Session Validation")
    is_valid = pm.validate_session(session_token)
    print(f"  Valid session: {is_valid}")
    assert is_valid == True, "Session should be valid"
    
    is_invalid = pm.validate_session("wrong-session-token")
    print(f"  Invalid session check: {is_invalid}")
    assert is_invalid == False, "Wrong session should be invalid"
    print("  PASSED")
    
    # Test 6: Get paired device info
    print("\n[Test 6] Get Paired Device Info")
    info = pm.get_paired_device_info()
    print(f"  Device name: {info['device_name']}")
    print(f"  Device ID: {info['device_id']}")
    print(f"  Paired at: {info['paired_at']}")
    assert 'session_token' not in info, "Session token should not be exposed"
    print("  PASSED")
    
    # Test 7: Pairing persistence (reload from file)
    print("\n[Test 7] Persistence Test")
    pm2 = PairingManager(data_dir=test_dir)
    assert pm2.is_paired() == True, "Should still be paired after reload"
    info2 = pm2.get_paired_device_info()
    assert info2['device_name'] == 'Test Phone', "Device info should persist"
    print(f"  Reloaded device: {info2['device_name']}")
    print("  PASSED")
    
    # Test 8: Re-pairing (new device replaces old)
    print("\n[Test 8] Re-pairing (Replace Old Device)")
    
    # Track if disconnect callback was called
    disconnect_called = {'called': False, 'token': None}
    def on_disconnect(old_token):
        disconnect_called['called'] = True
        disconnect_called['token'] = old_token
    
    pm2.set_disconnect_callback(on_disconnect)
    
    # Generate new token and pair new device
    new_token = pm2.generate_pairing_token()
    print(f"  New token: {new_token}")
    
    result = pm2.validate_and_pair(new_token, {
        'device_id': 'test-device-2',
        'device_name': 'New Tablet',
        'user_agent': 'Mozilla/5.0 (Android; Tablet)'
    })
    
    print(f"  New pairing success: {result['success']}")
    print(f"  Disconnect callback called: {disconnect_called['called']}")
    assert result['success'] == True, "New device should pair"
    assert disconnect_called['called'] == True, "Should call disconnect callback"
    
    new_info = pm2.get_paired_device_info()
    assert new_info['device_name'] == 'New Tablet', "New device should be paired"
    print(f"  Now paired to: {new_info['device_name']}")
    print("  PASSED")
    
    # Test 9: Local request detection
    print("\n[Test 9] Local Request Detection")
    assert pm2.is_local_request('127.0.0.1') == True, "127.0.0.1 should be local"
    assert pm2.is_local_request('::1') == True, "::1 should be local"
    assert pm2.is_local_request('192.168.1.100') == False, "192.168.x.x should be remote"
    print("  127.0.0.1 → local: True")
    print("  192.168.1.100 → local: False")
    print("  PASSED")
    
    # Test 10: Unpair
    print("\n[Test 10] Unpair Device")
    unpaired = pm2.unpair()
    assert unpaired == True, "Should return True when unpairing"
    assert pm2.is_paired() == False, "Should not be paired after unpair"
    print(f"  Unpaired: {unpaired}")
    print(f"  Is paired now: {pm2.is_paired()}")
    print("  PASSED")
    
    # Test 11: Unpair when not paired
    print("\n[Test 11] Unpair When Not Paired")
    unpaired_again = pm2.unpair()
    assert unpaired_again == False, "Should return False when nothing to unpair"
    print(f"  Unpair result: {unpaired_again}")
    print("  PASSED")
    
    # Test 12: Get status
    print("\n[Test 12] Get Full Status")
    status = pm2.get_status()
    print(f"  Status: {status}")
    assert 'is_paired' in status
    assert 'paired_device' in status
    assert 'has_pending_token' in status
    print("  PASSED")
    
    # Cleanup test file
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
    
    # Cleanup
    test_file = os.path.join(test_dir, 'pairing.json')
    if os.path.exists(test_file):
        os.remove(test_file)
        print(f"\nCleaned up test file: {test_file}")
    
    print("\nPhase 1 (PairingManager) is working correctly!")
    print("   You can proceed to Phase 2 (API Endpoints)")


if __name__ == '__main__':
    test_pairing_manager()
