import unittest
from unittest.mock import patch

from gmc605_connector.cli import main, resolve_mode, resolve_serial_port


class InteractiveCliTests(unittest.TestCase):
    def test_explicit_mode_does_not_prompt(self) -> None:
        with patch("builtins.input", side_effect=AssertionError("unexpected prompt")):
            self.assertEqual(resolve_mode("msfs"), "msfs")

    def test_interactive_mode_defaults_to_debug(self) -> None:
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("builtins.input", return_value=""),
        ):
            self.assertEqual(resolve_mode(None), "debug")

    def test_noninteractive_mode_defaults_to_auto(self) -> None:
        with patch("sys.stdin.isatty", return_value=False):
            self.assertEqual(resolve_mode(None), "auto")

    def test_interactive_port_selects_detected_port(self) -> None:
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch(
                "gmc605_connector.cli.available_serial_ports",
                return_value=[("COM5", "ESP32"), ("COM8", "Other")],
            ),
            patch("builtins.input", return_value="2"),
        ):
            self.assertEqual(resolve_serial_port(), "COM8")

    def test_web_launch_without_mode_does_not_prompt(self) -> None:
        with (
            patch("builtins.input", side_effect=AssertionError("unexpected prompt")),
            patch("gmc605_connector.cli.run_web_server", return_value=0),
        ):
            self.assertEqual(main(["--web"]), 0)


if __name__ == "__main__":
    unittest.main()
