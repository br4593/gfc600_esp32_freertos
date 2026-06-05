import unittest

from gmc605_connector.model import Deviation


class DeviationTests(unittest.TestCase):
    def test_half_scale_threshold(self) -> None:
        self.assertEqual(Deviation.from_needle(True, 63).half_scale, "LESS")
        self.assertEqual(Deviation.from_needle(True, 64).half_scale, "GREATER")
        self.assertEqual(Deviation.from_needle(True, -64).half_scale, "GREATER")

    def test_invalid_deviation(self) -> None:
        deviation = Deviation.from_needle(False, 100)
        self.assertFalse(deviation.valid)
        self.assertEqual(deviation.half_scale, "INVALID")

    def test_needle_is_clamped(self) -> None:
        self.assertEqual(Deviation.from_needle(True, 500).needle, 127)
        self.assertEqual(Deviation.from_needle(True, -500).needle, -127)


if __name__ == "__main__":
    unittest.main()

