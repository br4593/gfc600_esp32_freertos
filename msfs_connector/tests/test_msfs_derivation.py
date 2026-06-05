import unittest

from gmc605_connector.msfs_source import derive_snapshot


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
                "AUTOPILOT_APPROACH_ACTIVE": 1,
                "AUTOPILOT_GLIDESLOPE_ACTIVE": 1,
                "HSI_HAS_LOCALIZER": 1,
                "HSI_CDI_NEEDLE_VALID": 1,
                "HSI_CDI_NEEDLE": 20,
            }
        )
        self.assertEqual(snapshot.nav_source, "LOC")
        self.assertEqual(snapshot.lat_active, "LOC")
        self.assertEqual(snapshot.vert_active, "GS")

    def test_vor_approach_annunciates_vapp(self) -> None:
        snapshot = derive_snapshot(
            {
                "AUTOPILOT_FLIGHT_DIRECTOR_ACTIVE": 1,
                "AUTOPILOT_APPROACH_ARM": 1,
                "HSI_CDI_NEEDLE_VALID": 1,
                "HSI_CDI_NEEDLE": 90,
            }
        )
        self.assertEqual(snapshot.nav_source, "VOR")
        self.assertEqual(snapshot.lat_armed, "VAPP")


if __name__ == "__main__":
    unittest.main()
