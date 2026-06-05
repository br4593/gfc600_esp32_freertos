import unittest

from gmc605_connector.debug_source import DebugSource
from gmc605_connector.model import Command


class DebugSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = DebugSource()

    def command(self, name: str, value=None) -> None:
        result = self.source.handle_command(Command(seq=1, command=name, value=value))
        self.assertTrue(result.accepted, result.message)

    def test_ap_press_enables_defaults(self) -> None:
        self.command("AP_PRESS")
        snapshot = self.source.poll()
        self.assertTrue(snapshot.ap)
        self.assertTrue(snapshot.fd)
        self.assertEqual(snapshot.lat_active, "ROL")
        self.assertEqual(snapshot.vert_active, "PIT")

    def test_nav_arms_then_captures(self) -> None:
        self.command("DEBUG_SET_NAV_SOURCE", "GPS")
        self.command("DEBUG_SET_CDI", 90)
        self.command("NAV_PRESS")
        snapshot = self.source.poll()
        self.assertEqual(snapshot.lat_active, "ROL")
        self.assertEqual(snapshot.lat_armed, "GPS")

        self.command("DEBUG_CAPTURE_LATERAL")
        snapshot = self.source.poll()
        self.assertEqual(snapshot.lat_active, "GPS")
        self.assertEqual(snapshot.lat_armed, "NONE")

    def test_apr_arms_glideslope(self) -> None:
        self.command("DEBUG_SET_NAV_SOURCE", "LOC")
        self.command("DEBUG_SET_CDI", 90)
        self.command("APR_PRESS")
        snapshot = self.source.poll()
        self.assertEqual(snapshot.lat_armed, "LOC")
        self.assertIn("GS", snapshot.vert_armed)

        self.command("APR_PRESS")
        snapshot = self.source.poll()
        self.assertEqual(snapshot.lat_armed, "NONE")
        self.assertNotIn("GS", snapshot.vert_armed)

    def test_debug_set_snapshot_overrides_display_fields(self) -> None:
        self.command(
            "DEBUG_SET_SNAPSHOT",
            {
                "sim_connected": False,
                "ap": True,
                "fd": True,
                "yd": True,
                "nav_source": "LOC",
                "lat_active": "HDG",
                "lat_armed": "LOC",
                "vert_active": "VS",
                "vert_armed": ["ALTS", "GS"],
                "references": {
                    "heading_deg": 275,
                    "altitude_ft": 7000,
                    "vs_fpm": -500,
                    "speed_kt": 145,
                },
                "aircraft": {
                    "heading_deg": 260,
                    "altitude_ft": 6200,
                    "vs_fpm": -300,
                    "airspeed_kt": 138,
                },
                "cdi": {"valid": True, "needle": 80},
                "gsi": {"valid": True, "needle": -45},
                "messages": ["no sim", "trim"],
            },
        )

        snapshot = self.source.poll()
        self.assertFalse(snapshot.sim_connected)
        self.assertTrue(snapshot.ap)
        self.assertTrue(snapshot.fd)
        self.assertTrue(snapshot.yd)
        self.assertEqual(snapshot.nav_source, "LOC")
        self.assertEqual(snapshot.lat_active, "HDG")
        self.assertEqual(snapshot.lat_armed, "LOC")
        self.assertEqual(snapshot.vert_active, "VS")
        self.assertEqual(snapshot.vert_armed, ["ALTS", "GS"])
        self.assertEqual(snapshot.references.heading_deg, 275)
        self.assertEqual(snapshot.references.altitude_ft, 7000)
        self.assertEqual(snapshot.references.vs_fpm, -500)
        self.assertEqual(snapshot.references.speed_kt, 145)
        self.assertEqual(snapshot.aircraft.airspeed_kt, 138)
        self.assertTrue(snapshot.cdi.valid)
        self.assertEqual(snapshot.cdi.needle, 80)
        self.assertEqual(snapshot.gsi.needle, -45)
        self.assertEqual(snapshot.messages, ["no sim", "trim"])


if __name__ == "__main__":
    unittest.main()
