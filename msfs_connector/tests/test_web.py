import threading
import time
import unittest

from gmc605_connector.debug_source import DebugSource
from gmc605_connector.source import SnapshotSource
from gmc605_connector.transport import MemoryTransport
from gmc605_connector.web import (
    INDEX_HTML,
    PANEL_IMAGE_PATH,
    WebConnectorApp,
    serial_port_status,
)


class WebConnectorAppTests(unittest.TestCase):
    def test_html_contains_graphic_panel_annunciators(self) -> None:
        self.assertIn("GMC 605", INDEX_HTML)
        self.assertTrue(PANEL_IMAGE_PATH.exists())
        self.assertIn("/assets/gmc605_panel.svg", INDEX_HTML)
        self.assertIn('class="image-lcd"', INDEX_HTML)
        self.assertIn('id="display-lat-active"', INDEX_HTML)
        self.assertIn('id="display-lat-armed"', INDEX_HTML)
        self.assertIn('id="display-vert-active"', INDEX_HTML)
        self.assertIn('id="display-vert-armed"', INDEX_HTML)
        self.assertIn('class="hotspot hdg-key"', INDEX_HTML)
        self.assertIn('class="hotspot apr-key"', INDEX_HTML)
        self.assertIn('id="nav-source-control"', INDEX_HTML)
        self.assertIn('id="mode-control"', INDEX_HTML)
        self.assertIn('"/api/mode"', INDEX_HTML)
        self.assertIn('id="uart-port-control"', INDEX_HTML)
        self.assertIn('id="uart-port-list"', INDEX_HTML)
        self.assertIn("No serial ports detected", INDEX_HTML)
        self.assertIn('"/api/transport"', INDEX_HTML)
        self.assertIn('id="uart-rx"', INDEX_HTML)
        self.assertIn('"/api/uart-rx/clear"', INDEX_HTML)
        self.assertIn('id="uart-tx"', INDEX_HTML)
        self.assertIn('"/api/uart-tx/clear"', INDEX_HTML)
        self.assertIn('data-preset="cruise"', INDEX_HTML)
        self.assertIn('data-quick-nav="LOC"', INDEX_HTML)
        self.assertIn('data-snap-step="airAltitude"', INDEX_HTML)
        self.assertIn("DEBUG_SET_SNAPSHOT", INDEX_HTML)
        self.assertIn("function panelModeValue", INDEX_HTML)
        self.assertIn('"VAPP"', INDEX_HTML)
        self.assertNotIn("GPS_NAV", INDEX_HTML)

    def test_status_updates_and_web_command_changes_snapshot(self) -> None:
        app = WebConnectorApp(source=DebugSource(), update_hz=50.0)
        app.start()
        try:
            deadline = time.monotonic() + 1.0
            status = app.status()
            while status["snapshot"] is None and time.monotonic() < deadline:
                time.sleep(0.02)
                status = app.status()

            self.assertTrue(status["source_open"])
            self.assertIsNotNone(status["snapshot"])

            response = app.send_web_command("AP_PRESS")
            self.assertTrue(response["result"]["accepted"])
            self.assertTrue(response["snapshot"]["ap"])
            self.assertTrue(response["snapshot"]["fd"])
        finally:
            app.stop()

    def test_start_and_stop_do_not_wait_for_blocked_source_open(self) -> None:
        source = BlockingSource()
        app = WebConnectorApp(source=source)

        started = time.monotonic()
        app.start()
        self.assertLess(time.monotonic() - started, 0.25)
        self.assertTrue(app.status()["running"])

        stopped = time.monotonic()
        app.stop()
        self.assertLess(time.monotonic() - stopped, 2.5)

    def test_select_mode_replaces_source(self) -> None:
        app = WebConnectorApp(
            source=DebugSource(),
            update_hz=50.0,
            source_factories={"replacement": DebugSource},
            selected_mode="debug",
        )
        app.start()
        try:
            app.select_mode("replacement")
            deadline = time.monotonic() + 1.0
            status = app.status()
            while (
                (status["mode"] != "replacement" or not status["source_open"])
                and time.monotonic() < deadline
            ):
                time.sleep(0.02)
                status = app.status()

            self.assertEqual(status["mode"], "replacement")
            self.assertEqual(status["source"], "debug")
            self.assertTrue(status["source_open"])
        finally:
            app.stop()

    def test_configure_uart_replaces_and_disconnects_transport(self) -> None:
        created: list[TrackingTransport] = []

        def transport_factory(port: str, baudrate: int) -> TrackingTransport:
            transport = TrackingTransport(port, baudrate)
            created.append(transport)
            return transport

        app = WebConnectorApp(
            source=DebugSource(),
            update_hz=50.0,
            transport_factory=transport_factory,
        )
        app.start()
        try:
            app.configure_uart("COM7", 230400)
            deadline = time.monotonic() + 1.0
            status = app.status()
            while not status["transport_open"] and time.monotonic() < deadline:
                time.sleep(0.02)
                status = app.status()

            self.assertEqual(status["transport_port"], "COM7")
            self.assertEqual(status["baudrate"], 230400)
            self.assertTrue(status["transport_open"])
            self.assertEqual(created[0].port, "COM7")
            self.assertEqual(created[0].baudrate, 230400)
            self.assertGreaterEqual(created[0].open_count, 1)

            app.configure_uart(None)
            deadline = time.monotonic() + 1.0
            status = app.status()
            while status["transport_enabled"] and time.monotonic() < deadline:
                time.sleep(0.02)
                status = app.status()

            self.assertFalse(status["transport_enabled"])
            self.assertIsNone(status["transport_port"])
            self.assertGreaterEqual(created[0].close_count, 1)
        finally:
            app.stop()

    def test_uart_receive_monitor_captures_and_clears_messages(self) -> None:
        transport = MemoryTransport()
        app = WebConnectorApp(source=DebugSource(), transport=transport, update_hz=50.0)
        app.start()
        try:
            deadline = time.monotonic() + 1.0
            while not app.status()["transport_open"] and time.monotonic() < deadline:
                time.sleep(0.02)
            transport.incoming.append(
                {"v": 1, "type": "command", "seq": 8, "command": "AP_PRESS"}
            )
            deadline = time.monotonic() + 1.0
            while not app.status()["uart_rx"] and time.monotonic() < deadline:
                time.sleep(0.02)

            self.assertIn('"command":"AP_PRESS"', app.status()["uart_rx"][0])
            self.assertTrue(app.status()["uart_tx"])
            self.assertEqual(app.clear_uart_rx()["uart_rx"], [])
            self.assertEqual(app.clear_uart_tx()["uart_tx"], [])
        finally:
            app.stop()

    def test_serial_port_status_reports_dependency_or_ports(self) -> None:
        status = serial_port_status()
        self.assertIn("ports", status)
        self.assertIn("error", status)


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


class TrackingTransport(MemoryTransport):
    def __init__(self, port: str, baudrate: int) -> None:
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.open_count = 0
        self.close_count = 0

    def open(self) -> None:
        self.open_count += 1

    def close(self) -> None:
        self.close_count += 1


if __name__ == "__main__":
    unittest.main()
