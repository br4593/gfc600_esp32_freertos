from __future__ import annotations

import argparse
import logging
import sys

from .auto_source import AutoSource
from .connector import Connector
from .debug_source import DebugSource
from .msfs_source import MsfsSource
from .source import SnapshotSource
from .transport import SerialTransport, StdoutTransport
from .web import WebConnectorApp, run_web_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="MSFS/debug UART connector for the GMC 605 ESP32 panel"
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "msfs", "debug"),
        default=None,
        help=(
            "data source. auto: control MSFS when the sim is running, else "
            "fall back to debug. msfs: require MSFS. debug: never use MSFS. "
            "When omitted in a terminal, the connector asks."
        ),
    )
    parser.add_argument(
        "--transport",
        choices=("serial", "stdout"),
        default="serial",
        help="snapshot output transport",
    )
    parser.add_argument("--port", help="serial port, for example COM5")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--update-hz", type=float, default=10.0)
    parser.add_argument(
        "--source-open-timeout",
        type=float,
        default=5.0,
        help="seconds to wait for SimConnect/source startup before failing",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="run a local browser dashboard instead of the headless connector loop",
    )
    parser.add_argument("--web-host", default="127.0.0.1")
    parser.add_argument("--web-port", type=int, default=8765)
    parser.add_argument(
        "--snapshot-count",
        type=int,
        help="stop after sending this many snapshots",
    )
    parser.add_argument("--list-ports", action="store_true")
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.list_ports:
        return list_ports()

    args.mode = args.mode or "debug" if args.web else resolve_mode(args.mode)

    if not args.web and args.transport == "serial" and not args.port:
        args.port = resolve_serial_port()

    source = build_source(args.mode)

    if args.web:
        transport = build_transport(args, require_port=False)
        app = WebConnectorApp(
            source=source,
            transport=transport,
            update_hz=args.update_hz,
            source_factories={
                "auto": lambda: AutoSource(),
                "msfs": lambda: MsfsSource(),
                "debug": lambda: DebugSource(),
            },
            selected_mode=args.mode,
            transport_factory=lambda port, baudrate: SerialTransport(port, baudrate),
            selected_port=args.port,
            baudrate=args.baudrate,
        )
        return run_web_server(app, args.web_host, args.web_port)

    if args.transport == "serial" and not args.port:
        parser.error("--port is required for serial transport")

    transport = build_transport(args, require_port=True)

    connector = Connector(
        source=source,
        transport=transport,
        update_hz=args.update_hz,
        snapshot_count=args.snapshot_count,
        source_open_timeout_s=args.source_open_timeout,
    )
    try:
        connector.run()
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        logging.getLogger(__name__).exception("connector stopped")
        print(f"connector error: {exc}", file=sys.stderr)
        return 1
    return 0


def list_ports() -> int:
    ports = available_serial_ports()
    if ports is None:
        return 1
    if not ports:
        print("No serial ports found.")
        return 0

    for device, description in ports:
        print(f"{device}: {description}")
    return 0


def available_serial_ports() -> list[tuple[str, str]] | None:
    try:
        from serial.tools import list_ports as serial_list_ports
    except ImportError:
        print("pyserial is required to list serial ports", file=sys.stderr)
        return None

    return [(port.device, port.description) for port in serial_list_ports.comports()]


def resolve_mode(mode: str | None) -> str:
    if mode is not None:
        return mode
    if not sys.stdin.isatty():
        return "auto"

    print("Select connector mode:")
    print("  1. Debug - simulated data, MSFS not required")
    print("  2. MSFS  - connect to and control MSFS")

    while True:
        try:
            choice = input("Mode [1]: ").strip().lower()
        except EOFError:
            return "debug"

        if choice in {"", "1", "debug", "d"}:
            return "debug"
        if choice in {"2", "msfs", "m"}:
            return "msfs"
        print("Enter 1 for Debug or 2 for MSFS.")


def resolve_serial_port() -> str | None:
    if not sys.stdin.isatty():
        return None

    ports = available_serial_ports()
    if ports is None:
        return None

    if ports:
        print("Select ESP32 serial port:")
        for index, (device, description) in enumerate(ports, start=1):
            print(f"  {index}. {device} - {description}")
        prompt = f"Port [1 - {ports[0][0]}]: "
    else:
        print("No serial ports detected. Enter the ESP32 port manually.")
        prompt = "Port: "

    while True:
        try:
            choice = input(prompt).strip()
        except EOFError:
            return None

        if ports and choice == "":
            return ports[0][0]
        if choice.isdigit() and ports:
            index = int(choice) - 1
            if 0 <= index < len(ports):
                return ports[index][0]
        if choice:
            return choice
        print("A serial port is required.")


def build_source(mode: str) -> SnapshotSource:
    if mode == "debug":
        return DebugSource()
    if mode == "msfs":
        return MsfsSource()
    return AutoSource()


def build_transport(
    args: argparse.Namespace,
    require_port: bool,
) -> SerialTransport | StdoutTransport | None:
    if args.transport == "stdout":
        return StdoutTransport()
    if args.port:
        return SerialTransport(args.port, args.baudrate)
    if require_port:
        raise ValueError("serial port is required")
    logging.getLogger(__name__).info("web mode started without a serial transport")
    return None
