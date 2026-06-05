import time
import unittest

from gmc605_connector.debug_source import DebugSource
from gmc605_connector.web import INDEX_HTML, PANEL_IMAGE_PATH, WebConnectorApp


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


if __name__ == "__main__":
    unittest.main()
