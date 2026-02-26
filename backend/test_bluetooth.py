import unittest
from unittest.mock import patch, MagicMock
from bluetooth_mgmt import BluetoothManager

class TestBluetoothManager(unittest.TestCase):

    def setUp(self):
        # Create a mock config dict
        self.mock_config = {
            "bluetooth.enabled": True,
            "bluetooth.auto_connect": False,
            "bluetooth.preferred_mac": "00:11:22:33:44:55"
        }
        
        # We need to patch _run_cmd in init to avoid actual shell calls during setup
        with patch.object(BluetoothManager, '_run_cmd') as mock_run:
            mock_run.return_value = ("Success", "", 0)
            
            # Use a mock dict-like object for config
            mock_config_obj = MagicMock()
            mock_config_obj.get.side_effect = lambda k, d=None: self.mock_config.get(k, d)
            
            self.manager = BluetoothManager(config=mock_config_obj)

    @patch('bluetooth_mgmt.subprocess.run')
    def test_run_cmd_success(self, mock_run):
        mock_process = MagicMock()
        mock_process.stdout = "output"
        mock_process.stderr = ""
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        out, err, code = self.manager._run_cmd(["echo", "hello"])
        self.assertEqual(out, "output")
        self.assertEqual(code, 0)

    @patch('bluetooth_mgmt.subprocess.run')
    def test_status_connected(self, mock_run):
        mock_process = MagicMock()
        mock_process.stdout = "Device 00:11:22:33:44:55 MySpeaker\nConnected: yes\nName: MySpeaker"
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        status = self.manager.status()
        self.assertTrue(status["connected"])
        self.assertEqual(status["mac"], "00:11:22:33:44:55")
        self.assertEqual(status["device"], "MySpeaker")

    @patch('bluetooth_mgmt.subprocess.run')
    def test_status_disconnected(self, mock_run):
        mock_process = MagicMock()
        mock_process.stdout = "Missing device address"
        mock_process.returncode = 1
        mock_run.return_value = mock_process
        
        status = self.manager.status()
        self.assertFalse(status["connected"])
        self.assertIsNone(status["mac"])

    @patch.object(BluetoothManager, '_run_cmd')
    def test_scan(self, mock_run_cmd):
        # Scan triggers 3 run_cmd calls: scan on, scan off, devices
        mock_run_cmd.side_effect = [
            ("Discovery started", "", 0),
            ("Discovery stopped", "", 0),
            ("Device AA:BB:CC:DD:EE:FF Speaker1\nDevice 11:22:33:44:55:66 Speaker2", "", 0),
            # Mocking the _is_known calls that happen within scan loop
            ("Paired: yes", "", 0),
            ("Trusted: no", "", 0)
        ]
        
        # Mock time.sleep to run fast
        with patch('bluetooth_mgmt.time.sleep'):
            devices = self.manager.scan(duration=1)
            
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0]["mac"], "AA:BB:CC:DD:EE:FF")
        self.assertEqual(devices[0]["name"], "Speaker1")
        self.assertTrue(devices[0]["known"]) # Because we mocked _is_known to return True for first device
        
    @patch.object(BluetoothManager, '_run_cmd')
    @patch.object(BluetoothManager, '_is_known', return_value=True)
    @patch.object(BluetoothManager, '_set_pulse_sink')
    def test_connect_known_device_success(self, mock_set_sink, mock_is_known, mock_run_cmd):
        mock_run_cmd.return_value = ("Connection successful", "", 0)
        
        success, msg = self.manager.connect("00:11:22:33:44:55")
        
        self.assertTrue(success)
        mock_run_cmd.assert_called_with(["bluetoothctl", "connect", "00:11:22:33:44:55"], timeout=15)
        mock_set_sink.assert_called_once()
        self.manager.config.set.assert_called_with("bluetooth.preferred_mac", "00:11:22:33:44:55", save=True)

    @patch.object(BluetoothManager, '_run_cmd')
    def test_disconnect_success(self, mock_run_cmd):
        mock_run_cmd.return_value = ("Successful disconnected", "", 0)
        
        success, msg = self.manager.disconnect("00:11:22:33:44:55")
        
        self.assertTrue(success)
        mock_run_cmd.assert_called_with(["bluetoothctl", "disconnect", "00:11:22:33:44:55"])

if __name__ == '__main__':
    unittest.main()
