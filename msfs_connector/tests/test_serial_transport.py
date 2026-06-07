import time
import unittest

from gmc605_connector.transport import SerialTransport

try:
    import serial  # noqa: F401
except ImportError:
    serial = None


class SerialTransportTests(unittest.TestCase):
    @unittest.skipIf(serial is None, "pyserial is not installed")
    def test_pyserial_loopback(self) -> None:
        transport = SerialTransport("loop://", 115200)
        transport.open()
        try:
            transport.send({"v": 1, "type": "command", "seq": 1, "command": "AP_PRESS"})
            time.sleep(0.01)
            messages = transport.receive()
        finally:
            transport.close()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["command"], "AP_PRESS")
        self.assertIn('"command":"AP_PRESS"', messages[0]["_raw"])

    @unittest.skipIf(serial is None, "pyserial is not installed")
    def test_non_json_serial_output_is_preserved_as_raw_text(self) -> None:
        transport = SerialTransport("loop://", 115200)
        transport.open()
        try:
            transport._serial.write(b"I (123) app: ESP32 ready\n")
            time.sleep(0.01)
            messages = transport.receive()
        finally:
            transport.close()

        self.assertEqual(
            messages,
            [{"v": 1, "type": "_transport_raw", "raw": "I (123) app: ESP32 ready"}],
        )


if __name__ == "__main__":
    unittest.main()
