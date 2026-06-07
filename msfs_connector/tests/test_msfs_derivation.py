import unittest

from gmc605_connector.model import Command
from gmc605_connector.msfs_source import _SIMVAR_DEFS, MsfsSource, derive_snapshot


class MsfsDerivationTests(unittest.TestCase):
    def test_gps_nav_and_altitude_arm(self) -> None:
        snapshot = derive_snapshot(
            {
                "AUTOPILOT_MASTER": 1,
                "AUTOPILOT_FLIGHT_DIRECTOR_ACTIVE": 1,
                "AUTOPILOT_NAV1_LOCK": 1,
                "GPS_DRIVES_NAV1": 1,
                "HSI_CDI_NEEDLE_VALID": 1,
                "HSI_CDI_NEEDLE": 80,
                "AUTOPILOT_VERTICAL_HOLD": 1,
                "AUTOPILOT_ALTITUDE_ARM": 1,
            }
        )
        self.assertEqual(snapshot.nav_source, "GPS")
        self.assertEqual(snapshot.lat_active, "GPS")
        self.assertEqual(snapshot.vert_active, "VS")
        self.assertIn("ALTS", snapshot.vert_armed)

    def test_loc_approach_and_glideslope(self) -> None:
        snapshot = derive_snapshot(
            {
                "AUTOPILOT_FLIGHT_DIRECTOR_ACTIVE": 1,
                "AUTOPILOT_APPROACH_HOLD": 1,
                "AUTOPILOT_GLIDESLOPE_ACTIVE": 1,
                "HSI_HAS_LOCALIZER": 1,
                "HSI_CDI_NEEDLE_VALID": 1,
                "HSI_CDI_NEEDLE": 20,
            }
        )
        self.assertEqual(snapshot.nav_source, "LOC")
        self.assertEqual(snapshot.lat_active, "LOC")
        self.assertEqual(snapshot.vert_active, "GS")

    def test_generic_approach_arm_does_not_invent_vapp_armed(self) -> None:
        snapshot = derive_snapshot(
            {
                "AUTOPILOT_FLIGHT_DIRECTOR_ACTIVE": 1,
                "AUTOPILOT_APPROACH_ARM": 1,
                "HSI_CDI_NEEDLE_VALID": 1,
                "HSI_CDI_NEEDLE": 90,
            }
        )
        self.assertEqual(snapshot.nav_source, "VOR")
        self.assertEqual(snapshot.lat_armed, "NONE")

    def test_generic_glideslope_state_does_not_invent_gps_glidepath(self) -> None:
        snapshot = derive_snapshot(
            {
                "AUTOPILOT_FLIGHT_DIRECTOR_ACTIVE": 1,
                "GPS_DRIVES_NAV1": 1,
                "AUTOPILOT_GLIDESLOPE_ACTIVE": 1,
            }
        )
        self.assertEqual(snapshot.nav_source, "GPS")
        self.assertEqual(snapshot.vert_active, "PIT")
        self.assertNotIn("GP", snapshot.vert_armed)

    def test_approach_localizer_var_identifies_active_approach_only(self) -> None:
        snapshot = derive_snapshot(
            {
                "AUTOPILOT_FLIGHT_DIRECTOR_ACTIVE": 1,
                "AUTOPILOT_APPROACH_IS_LOCALIZER": 1,
                "AUTOPILOT_APPROACH_HOLD": 1,
            }
        )
        self.assertEqual(snapshot.nav_source, "LOC")
        self.assertEqual(snapshot.lat_active, "LOC")

        not_active = derive_snapshot(
            {
                "AUTOPILOT_FLIGHT_DIRECTOR_ACTIVE": 1,
                "AUTOPILOT_APPROACH_IS_LOCALIZER": 1,
            }
        )
        self.assertEqual(not_active.nav_source, "NONE")
        self.assertEqual(not_active.lat_active, "ROL")

    def test_gsi_is_normalized_from_msfs_range_to_protocol_range(self) -> None:
        snapshot = derive_snapshot(
            {
                "HSI_GSI_NEEDLE_VALID": 1,
                "HSI_GSI_NEEDLE": 119,
            }
        )
        self.assertEqual(snapshot.gsi.needle, 127)

    def test_requested_simvars_exclude_misleading_arm_vars(self) -> None:
        self.assertNotIn("AUTOPILOT_APPROACH_ARM", _SIMVAR_DEFS)
        self.assertNotIn("AUTOPILOT_GLIDESLOPE_ARM", _SIMVAR_DEFS)
        self.assertEqual(
            _SIMVAR_DEFS["AUTOPILOT_VERTICAL_HOLD_VAR"][1], b"Feet/minute"
        )

    def test_approach_selected_state_controls_apr_and_nav_events(self) -> None:
        source = MsfsSource()
        source._last_approach_selected = True
        source._last_snapshot = derive_snapshot(
            {
                "AUTOPILOT_FLIGHT_DIRECTOR_ACTIVE": 1,
                "AUTOPILOT_APPROACH_HOLD": 1,
                "AUTOPILOT_APPROACH_IS_LOCALIZER": 1,
            }
        )

        self.assertEqual(
            source._map_command(Command(1, "APR_PRESS")), ("AP_APR_HOLD_OFF", None)
        )
        self.assertEqual(
            source._map_command(Command(2, "NAV_PRESS")), ("AP_NAV1_HOLD_ON", None)
        )

    def test_reference_commands_are_normalized_before_transmit(self) -> None:
        source = MsfsSource()
        self.assertEqual(
            source._map_command(Command(1, "HEADING_SET", -1)),
            ("HEADING_BUG_SET", 359),
        )
        self.assertEqual(
            source._map_command(Command(2, "SPEED_SET", -10)),
            ("AP_SPD_VAR_SET", 0),
        )


if __name__ == "__main__":
    unittest.main()
