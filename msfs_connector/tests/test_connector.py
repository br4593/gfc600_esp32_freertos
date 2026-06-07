import threading
import time
import unittest

from gmc605_connector.connector import Connector
from gmc605_connector.debug_source import DebugSource
from gmc605_connector.source import SnapshotSource
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

    def test_blocked_source_open_times_out(self) -> None:
        source = BlockingSource()
        connector = Connector(
            source=source,
            transport=MemoryTransport(),
            source_open_timeout_s=0.05,
        )

        started = time.monotonic()
        with self.assertRaisesRegex(TimeoutError, "source open timed out"):
            connector.run()

        self.assertLess(time.monotonic() - started, 0.5)

    def test_blocked_source_close_is_bounded(self) -> None:
        source = BlockingCloseSource()
        connector = Connector(
            source=source,
            transport=MemoryTransport(),
            snapshot_count=1,
        )

        started = time.monotonic()
        connector.run()

        self.assertLess(time.monotonic() - started, 1.5)


class BlockingSource(SnapshotSource):
    name = "blocking"

    def __init__(self) -> None:
        self.release = threading.Event()

    def open(self) -> None:
        self.release.wait()

    def close(self) -> None:
        self.release.set()

    def poll(self):
        raise AssertionError("poll must not be called")

    def handle_command(self, command):
        raise AssertionError("handle_command must not be called")


class BlockingCloseSource(DebugSource):
    def close(self) -> None:
        threading.Event().wait()


if __name__ == "__main__":
    unittest.main()
