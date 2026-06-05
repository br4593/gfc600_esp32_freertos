import unittest

from gmc605_connector.protocol import (
    ProtocolError,
    decode_message,
    encode_message,
    parse_command,
)


class ProtocolTests(unittest.TestCase):
    def test_command_round_trip(self) -> None:
        encoded = encode_message(
            {
                "v": 1,
                "type": "command",
                "seq": 4,
                "command": "hdg_press",
            }
        )
        command = parse_command(decode_message(encoded))
        self.assertEqual(command.seq, 4)
        self.assertEqual(command.command, "HDG_PRESS")

    def test_rejects_unknown_version(self) -> None:
        with self.assertRaises(ProtocolError):
            decode_message('{"v":2,"type":"command","seq":1,"command":"AP_PRESS"}')


if __name__ == "__main__":
    unittest.main()

