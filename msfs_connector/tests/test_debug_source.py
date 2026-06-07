import unittest

from gmc605_connector.debug_source import DebugSource
from gmc605_connector.model import Command
from gmc605_connector.msfs_source import derive_snapshot


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

    def test_debug_set_snapshot_is_atomic_when_validation_fails(self) -> None:
        result = self.source.handle_command(
            Command(
                seq=1,
                command="DEBUG_SET_SNAPSHOT",
                value={"ap": True, "lat_active": "BAD_MODE"},
            )
        )

        self.assertFalse(result.accepted)
        snapshot = self.source.poll()
        self.assertFalse(snapshot.ap)
        self.assertEqual(snapshot.lat_active, "NONE")

    def test_debug_snapshot_enforces_live_output_invariants(self) -> None:
        self.command(
            "DEBUG_SET_SNAPSHOT",
            {
                "ap": True,
                "fd": False,
                "lat_active": "HDG",
                "vert_active": "VS",
            },
        )
        snapshot = self.source.poll()
        self.assertTrue(snapshot.fd)
        self.assertEqual(snapshot.lat_active, "HDG")

        self.command(
            "DEBUG_SET_SNAPSHOT",
            {"ap": False, "fd": True, "lat_active": "NONE", "vert_active": "NONE"},
        )
        snapshot = self.source.poll()
        self.assertEqual(snapshot.lat_active, "ROL")
        self.assertEqual(snapshot.vert_active, "PIT")

        self.command("DEBUG_SET_SNAPSHOT", {"ap": False, "fd": False})
        snapshot = self.source.poll()
        self.assertEqual(snapshot.lat_active, "NONE")
        self.assertEqual(snapshot.vert_active, "NONE")
        self.assertEqual(snapshot.vert_armed, [])

    def test_debug_poll_returns_an_independent_snapshot(self) -> None:
        snapshot = self.source.poll()
        snapshot.ap = True
        self.assertFalse(self.source.poll().ap)

    def test_debug_rejects_non_numeric_reference_without_changing_it(self) -> None:
        result = self.source.handle_command(
            Command(seq=1, command="ALTITUDE_SET", value="6000")
        )
        self.assertFalse(result.accepted)
        self.assertEqual(self.source.poll().references.altitude_ft, 5000)

    def test_debug_and_msfs_snapshots_have_the_same_output_shape(self) -> None:
        debug_message = self.source.poll().to_message()
        msfs_message = derive_snapshot({}).to_message()

        self.assertEqual(set(debug_message), set(msfs_message))
        for field in ("cdi", "gsi", "references", "aircraft"):
            self.assertEqual(set(debug_message[field]), set(msfs_message[field]))

    def test_debug_can_simulate_exact_generic_msfs_derivation(self) -> None:
        values = {
            "AUTOPILOT_MASTER": 1,
            "AUTOPILOT_HEADING_LOCK": 1,
            "AUTOPILOT_ALTITUDE_LOCK": 1,
            "AUTOPILOT_HEADING_LOCK_DIR": 275,
        }
        expected = derive_snapshot(values)

        self.command("DEBUG_SET_SIMVARS", values)
        actual = self.source.poll()

        self.assertEqual(actual.ap, expected.ap)
        self.assertEqual(actual.fd, expected.fd)
        self.assertEqual(actual.lat_active, expected.lat_active)
        self.assertEqual(actual.vert_active, expected.vert_active)
        self.assertEqual(actual.references, expected.references)
        self.assertEqual(actual.source, "debug")
        self.assertEqual(actual.messages, ["DEBUG SIMVARS"])


if __name__ == "__main__":
    unittest.main()
