import time
import unittest

from gmc605_connector.transport import SerialTransport


class SerialTransportTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

