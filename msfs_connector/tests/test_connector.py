import unittest

from gmc605_connector.connector import Connector
from gmc605_connector.debug_source import DebugSource
from gmc605_connector.transport import MemoryTransport


class ConnectorTests(unittest.TestCase):
    def test_command_result_and_snapshot_are_sent(self) -> None:
        source = DebugSource()
        transport = MemoryTransport()
        connector = Connector(source=source, transport=transport)
        transport.incoming.append(
            {
                "v": 1,
                "type": "command",
                "seq": 8,
                "command": "AP_PRESS",
            }
        )

        connector.process_incoming()

        self.assertEqual(transport.sent[0]["type"], "command_result")
        self.assertTrue(transport.sent[0]["accepted"])
        self.assertEqual(transport.sent[1]["type"], "snapshot")
        self.assertTrue(transport.sent[1]["ap"])


if __name__ == "__main__":
    unittest.main()

