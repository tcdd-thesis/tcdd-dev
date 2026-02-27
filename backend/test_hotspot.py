#!/usr/bin/env python3
"""
Test script for HotspotManager (Phase 1 - Ad-Hoc)
Run this on the Raspberry Pi to verify hotspot functionality.

NOTE: This test requires:
- Linux with NetworkManager installed
- WiFi hardware
- Root/sudo privileges for starting hotspot

Usage:
    cd /path/to/tcdd-dev
    sudo python backend/test_hotspot.py
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from hotspot import HotspotManager


class MockConfig:
    """Mock config for testing without full config.py dependency."""
    def __init__(self):
        self._data = {
            'pairing': {
                'enabled': True,
                'auto_start': True,
                'ssid': '',
                'password': '',
                'interface': 'wlan0'
            }
        }
    
    def get(self, key, default=None):
        parts = key.split('.')
        val = self._data
        for p in parts:
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                return default
        return val
    
    def set(self, key, value, save=True):
        parts = key.split('.')
        d = self._data
        for p in parts[:-1]:
            if p not in d:
                d[p] = {}
            d = d[p]
        d[parts[-1]] = value
    
    def save(self):
        pass  # Mock - no actual save


def test_hotspot_manager():
    """Run tests for HotspotManager"""
    
    print("=" * 60)
    print("Testing HotspotManager (Ad-Hoc WiFi)")
    print("=" * 60)
    
    # Create mock config
    mock_config = MockConfig()
    
    # Create instance with mock config
    hm = HotspotManager(config=mock_config)
    
    # Test 1: Check availability
    print("\n[Test 1] Check Hotspot Availability")
    available = hm.is_available()
    print(f"  Hotspot available: {available}")
    if not available:
        print("  Hotspot not available on this system")
        print("  This is expected on Windows or systems without NetworkManager")
        print("  On Raspberry Pi with NetworkManager, this should be True")
    print("  PASSED (check only)")
    
    # Test 2: Get credentials
    print("\n[Test 2] Get/Generate Credentials")
    creds = hm.get_credentials()
    print(f"  SSID: {creds['ssid']}")
    print(f"  Password: {creds['password']}")
    assert creds['ssid'] is not None, "SSID should not be None"
    assert creds['password'] is not None, "Password should not be None"
    assert len(creds['password']) >= 8, "Password should be at least 8 chars"
    print("  PASSED")
    
    # Test 3: Regenerate credentials
    print("\n[Test 3] Regenerate Credentials")
    old_ssid = creds['ssid']
    result = hm.regenerate_credentials()
    new_creds = hm.get_credentials()
    print(f"  Old SSID: {old_ssid}")
    print(f"  New SSID: {new_creds['ssid']}")
    print(f"  New Password: {new_creds['password']}")
    assert result['success'] == True, "Regenerate should succeed"
    # Note: There's a small chance the new SSID suffix could be the same
    print("  PASSED")
    
    # Test 4: Set custom credentials
    print("\n[Test 4] Set Custom Credentials")
    result = hm.set_credentials(ssid="TestNetwork", password="testpass123")
    print(f"  Result: {result}")
    creds = hm.get_credentials()
    assert creds['ssid'] == "TestNetwork", "SSID should be updated"
    assert creds['password'] == "testpass123", "Password should be updated"
    print("  PASSED")
    
    # Test 5: Validate password length
    print("\n[Test 5] Validate Password Length")
    result = hm.set_credentials(password="short")  # Too short
    print(f"  Short password result: {result}")
    assert result['success'] == False, "Should reject short password"
    print("  PASSED")
    
    # Test 6: Get status
    print("\n[Test 6] Get Status")
    status = hm.get_status()
    print(f"  Status: {status}")
    assert 'available' in status
    assert 'active' in status
    assert 'ssid' in status
    print("  PASSED")
    
    # Test 7: Persistence (via config)
    print("\n[Test 7] Persistence Test (via config)")
    hm.set_credentials(ssid="PersistTest", password="persist123")
    # Verify settings were written to mock config
    assert mock_config.get('pairing.ssid') == "PersistTest", "SSID should be in config"
    assert mock_config.get('pairing.password') == "persist123", "Password should be in config"
    # Create new instance with same config
    hm2 = HotspotManager(config=mock_config)
    creds2 = hm2.get_credentials()
    print(f"  Reloaded SSID: {creds2['ssid']}")
    assert creds2['ssid'] == "PersistTest", "SSID should persist"
    assert creds2['password'] == "persist123", "Password should persist"
    print("  PASSED")
    
    print("\n" + "=" * 60)
    print("Basic tests completed!")
    print("=" * 60)
    
    # Optional: Test actual hotspot start/stop
    # Only run if on Linux with NetworkManager
    if available:
        print("\n" + "=" * 60)
        print("OPTIONAL: Test Hotspot Start/Stop")
        print("=" * 60)
        print("\nWARNING: This will actually start a WiFi hotspot!")
        print("    Make sure you have sudo privileges.")
        
        response = input("\nDo you want to test hotspot start/stop? (y/N): ").strip().lower()
        
        if response == 'y':
            # Test start
            print("\n[Test A] Start Hotspot")
            result = hm2.start()
            print(f"  Result: {result}")
            
            if result['success']:
                print(f"  Hotspot started!")
                print(f"     SSID: {result.get('ssid')}")
                print(f"     Password: {result.get('password')}")
                print(f"     IP: {result.get('ip')}")
                
                input("\nPress Enter to stop the hotspot...")
                
                # Test stop
                print("\n[Test B] Stop Hotspot")
                result = hm2.stop()
                print(f"  Result: {result}")
                
                if result['success']:
                    print("  Hotspot stopped!")
                else:
                    print("  Stop may have failed, but WiFi should recover")
            else:
                print(f"  Could not start hotspot: {result.get('message')}")
                print("     This may require sudo privileges")
    else:
        print("\nTo test actual hotspot functionality:")
        print("   1. Run this script on a Raspberry Pi")
        print("   2. Ensure NetworkManager is installed")
        print("   3. Run with sudo: sudo python backend/test_hotspot.py")
    
    print("\nHotspotManager tests complete!")


def test_pairing_with_ip():
    """Test updated PairingManager with hotspot IP functionality"""
    
    print("\n" + "=" * 60)
    print("Testing PairingManager Hotspot IP Functions")
    print("=" * 60)
    
    from pairing import PairingManager, HOTSPOT_IP
    
    test_dir = 'data/test_pairing_ip'
    os.makedirs(test_dir, exist_ok=True)
    
    pm = PairingManager(data_dir=test_dir)
    
    # Test: Get hotspot IP (constant)
    print("\n[Test] Get Hotspot IP")
    ip = pm.get_hotspot_ip()
    print(f"  Hotspot IP: {ip}")
    assert ip == HOTSPOT_IP, f"IP should be {HOTSPOT_IP}"
    assert ip == '10.42.0.1', "IP should be 10.42.0.1"
    print("  PASSED")
    
    # Test: Generate pairing data
    print("\n[Test] Generate Pairing Data")
    data = pm.generate_pairing_data(port=80)
    print(f"  Token: {data['token']}")
    print(f"  IP: {data['ip']}")
    print(f"  URL: {data['url']}")
    assert 'token' in data
    assert 'url' in data
    assert data['ip'] == '10.42.0.1', "IP should be hotspot IP"
    assert data['token'] in data['url'], "Token should be in URL"
    print("  PASSED")
    
    # Test: Status includes hotspot IP
    print("\n[Test] Status Includes Hotspot IP")
    status = pm.get_status()
    print(f"  Status: {status}")
    assert 'hotspot_ip' in status, "Status should include hotspot_ip"
    assert status['hotspot_ip'] == '10.42.0.1', "Hotspot IP should be correct"
    print("  PASSED")
    
    # Cleanup
    import shutil
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    print("\nPairingManager IP tests complete!")


if __name__ == '__main__':
    test_hotspot_manager()
    test_pairing_with_ip()
