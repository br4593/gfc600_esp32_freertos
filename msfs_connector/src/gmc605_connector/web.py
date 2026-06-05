from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .model import Command, CommandResult, PanelSnapshot
from .protocol import ProtocolError, error_message, hello_message, parse_command
from .source import SnapshotSource
from .transport import Transport

LOGGER = logging.getLogger(__name__)
PANEL_IMAGE_PATH = Path(__file__).resolve().parent.parent / "img" / "gmc605_panel.svg"
LEGACY_PANEL_IMAGE_PATH = (
    Path(__file__).resolve().parent.parent / "img" / "gfc600_tinkercad.svg"
)


PANEL_COMMANDS = (
    "AP_PRESS",
    "FD_PRESS",
    "YD_PRESS",
    "AP_DISCONNECT",
    "HDG_PRESS",
    "NAV_PRESS",
    "APR_PRESS",
    "BC_PRESS",
    "ALT_PRESS",
    "VS_PRESS",
    "IAS_PRESS",
    "FLC_PRESS",
    "VNV_PRESS",
    "LVL_PRESS",
    "GA_PRESS",
)

REFERENCE_COMMANDS = (
    "HEADING_SET",
    "ALTITUDE_SET",
    "VS_SET",
    "SPEED_SET",
)

DEBUG_COMMANDS = (
    "DEBUG_RESET",
    "DEBUG_SET_NAV_SOURCE",
    "DEBUG_SET_CDI",
    "DEBUG_SET_GSI",
    "DEBUG_SET_SNAPSHOT",
    "DEBUG_CAPTURE_LATERAL",
    "DEBUG_CAPTURE_VERTICAL",
)


class WebConnectorApp:
    def __init__(
        self,
        source: SnapshotSource,
        transport: Transport | None = None,
        update_hz: float = 10.0,
    ) -> None:
        if update_hz <= 0:
            raise ValueError("update_hz must be greater than zero")
        self._source = source
        self._transport = transport
        self._update_hz = update_hz
        self._period_s = 1.0 / update_hz
        self._lock = threading.RLock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._snapshot_seq = 0
        self._command_seq = 0
        self._source_open = False
        self._transport_open = False
        self._last_snapshot: dict[str, Any] | None = None
        self._last_result: dict[str, Any] | None = None
        self._last_error = ""
        self._log: list[str] = []

    @property
    def source_name(self) -> str:
        return self._source.name

    @property
    def has_transport(self) -> bool:
        return self._transport is not None

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True

        self._try_open_source()
        self._try_open_transport()

        self._thread = threading.Thread(
            target=self._run_loop,
            name="gmc605-web-connector",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._close_source()
        self._close_transport()

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "source": self._source.name,
                "source_open": self._source_open,
                "transport_enabled": self._transport is not None,
                "transport_open": self._transport_open,
                "update_hz": self._update_hz,
                "last_error": self._last_error,
                "snapshot": self._last_snapshot,
                "last_result": self._last_result,
                "log": list(self._log[-12:]),
                "commands": {
                    "panel": list(PANEL_COMMANDS),
                    "reference": list(REFERENCE_COMMANDS),
                    "debug": list(DEBUG_COMMANDS),
                },
            }

    def send_web_command(self, name: str, value: Any = None) -> dict[str, Any]:
        with self._lock:
            self._command_seq += 1
            command = Command(seq=self._command_seq, command=name.upper(), value=value)

        result = self._handle_source_command(command)
        with self._lock:
            self._last_result = result.to_message()

        if result.accepted:
            self._send_snapshot()

        return {
            "result": result.to_message(),
            "snapshot": self.status()["snapshot"],
        }

    def _run_loop(self) -> None:
        next_snapshot = time.monotonic()
        next_source_retry = time.monotonic()
        next_transport_retry = time.monotonic()

        while self._is_running():
            now = time.monotonic()

            if not self._source_open and now >= next_source_retry:
                self._try_open_source()
                next_source_retry = now + 2.0

            if (
                self._transport is not None
                and not self._transport_open
                and now >= next_transport_retry
            ):
                self._try_open_transport()
                next_transport_retry = now + 2.0

            if self._transport_open:
                self._process_transport_incoming()

            if now >= next_snapshot:
                self._send_snapshot()
                next_snapshot = now + self._period_s

            time.sleep(min(0.02, max(0.0, next_snapshot - time.monotonic())))

    def _is_running(self) -> bool:
        with self._lock:
            return self._running

    def _try_open_source(self) -> None:
        with self._lock:
            if self._source_open:
                return
        try:
            self._source.open()
        except Exception as exc:
            self._record_error(f"source open failed: {exc}")
            return
        with self._lock:
            self._source_open = True
            self._last_error = ""
        self._record_log(f"{self._source.name} source opened")

    def _try_open_transport(self) -> None:
        if self._transport is None:
            return
        with self._lock:
            if self._transport_open:
                return
        try:
            self._transport.open()
            self._transport.send(hello_message(self._source.name, self._update_hz))
        except Exception as exc:
            self._record_error(f"transport open failed: {exc}")
            self._close_transport()
            return
        with self._lock:
            self._transport_open = True
            self._last_error = ""
        self._record_log("transport opened")

    def _close_source(self) -> None:
        try:
            self._source.close()
        except Exception:
            LOGGER.debug("source close failed", exc_info=True)
        with self._lock:
            self._source_open = False

    def _close_transport(self) -> None:
        if self._transport is None:
            return
        try:
            self._transport.close()
        except Exception:
            LOGGER.debug("transport close failed", exc_info=True)
        with self._lock:
            self._transport_open = False

    def _process_transport_incoming(self) -> None:
        if self._transport is None:
            return
        try:
            messages = self._transport.receive()
        except Exception as exc:
            self._record_error(f"transport receive failed: {exc}")
            self._close_transport()
            return

        for message in messages:
            if message.get("type") == "_transport_error":
                self._send_to_transport(error_message(str(message.get("message", ""))))
                continue

            try:
                command = parse_command(message)
            except ProtocolError as exc:
                self._send_to_transport(error_message(str(exc)))
                continue

            result = self._handle_source_command(command)
            result_message = result.to_message()
            with self._lock:
                self._last_result = result_message
            self._send_to_transport(result_message)
            self._send_snapshot()

    def _handle_source_command(self, command: Command) -> CommandResult:
        with self._lock:
            source_open = self._source_open
        if not source_open:
            return CommandResult(
                command_seq=command.seq,
                command=command.command,
                accepted=False,
                message="source is not open",
            )

        try:
            result = self._source.handle_command(command)
        except Exception as exc:
            LOGGER.exception("command failed: %s", command.command)
            return CommandResult(
                command_seq=command.seq,
                command=command.command,
                accepted=False,
                message=str(exc),
            )

        status = "accepted" if result.accepted else "rejected"
        self._record_log(f"{command.command} {status}: {result.message}")
        return result

    def _send_snapshot(self) -> None:
        with self._lock:
            if not self._source_open:
                return
        try:
            snapshot = self._source.poll()
        except Exception as exc:
            LOGGER.exception("snapshot poll failed")
            self._record_error(f"snapshot poll failed: {exc}")
            self._close_source()
            return

        message = self._snapshot_to_message(snapshot)
        with self._lock:
            self._last_snapshot = message
        self._send_to_transport(message)

    def _snapshot_to_message(self, snapshot: PanelSnapshot) -> dict[str, Any]:
        with self._lock:
            self._snapshot_seq += 1
            snapshot.seq = self._snapshot_seq
        snapshot.timestamp_ms = int(time.time() * 1000)
        return {"v": 1, "type": "snapshot", **asdict(snapshot)}

    def _send_to_transport(self, message: dict[str, Any]) -> None:
        if self._transport is None:
            return
        with self._lock:
            transport_open = self._transport_open
        if not transport_open:
            return
        try:
            self._transport.send(message)
        except Exception as exc:
            self._record_error(f"transport send failed: {exc}")
            self._close_transport()

    def _record_error(self, message: str) -> None:
        LOGGER.warning(message)
        with self._lock:
            self._last_error = message
            self._log.append(message)

    def _record_log(self, message: str) -> None:
        LOGGER.info(message)
        with self._lock:
            self._log.append(message)


def run_web_server(app: WebConnectorApp, host: str, port: int) -> int:
    app.start()
    server = ThreadingHTTPServer((host, port), build_handler(app))
    print(f"GMC 605 connector web UI: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
        app.stop()
    return 0


def build_handler(app: WebConnectorApp) -> type[BaseHTTPRequestHandler]:
    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/":
                self._send_text(INDEX_HTML, "text/html; charset=utf-8")
                return
            if path == "/api/status":
                self._send_json(app.status())
                return
            if path == "/api/ports":
                self._send_json({"ports": list_serial_ports()})
                return
            if path == "/assets/gmc605_panel.svg":
                self._send_file(PANEL_IMAGE_PATH, "image/svg+xml")
                return
            if path == "/assets/gfc600_tinkercad.svg":
                self._send_file(LEGACY_PANEL_IMAGE_PATH, "image/svg+xml")
                return
            self.send_error(HTTPStatus.NOT_FOUND, "not found")

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path != "/api/command":
                self.send_error(HTTPStatus.NOT_FOUND, "not found")
                return

            try:
                payload = self._read_json()
                command = payload["command"]
                value = payload.get("value")
                if not isinstance(command, str) or not command.strip():
                    raise ValueError("command is required")
            except Exception as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return

            self._send_json(app.send_web_command(command, value))

        def log_message(self, format: str, *args: Any) -> None:
            LOGGER.debug("web: " + format, *args)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8")) if raw else {}
            if not isinstance(data, dict):
                raise ValueError("request body must be a JSON object")
            return data

        def _send_json(
            self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK
        ) -> None:
            body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode(
                "utf-8"
            )
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, text: str, content_type: str) -> None:
            body = text.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_file(self, path: Path, content_type: str) -> None:
            if not path.exists() or not path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND, "not found")
                return
            body = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return DashboardHandler


def list_serial_ports() -> list[dict[str, str]]:
    try:
        from serial.tools import list_ports as serial_list_ports
    except ImportError:
        return []
    return [
        {"device": port.device, "description": port.description}
        for port in serial_list_ports.comports()
    ]


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GMC 605 MSFS Connector</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b0d10;
      --surface: #14181d;
      --line: #2d343b;
      --text: #eef3f6;
      --muted: #87909a;
      --green: #39ff5b;
      --green-dim: #1f7a33;
      --white: #e6eef0;
      --amber: #ffb43a;
      --red: #e3544f;
      --blue: #68a9ff;
      --cyan: #5fe3e3;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font: 14px/1.4 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      display: flex; align-items: center; justify-content: space-between;
      gap: 16px; padding: 14px 20px; border-bottom: 1px solid var(--line);
      background: #06080a; position: sticky; top: 0; z-index: 5;
    }
    h1, h2, h3 { margin: 0; font-weight: 650; letter-spacing: 0; }
    h1 { font-size: 18px; }
    h2 { font-size: 15px; margin-bottom: 12px; }
    h3 { font-size: 12px; color: var(--muted); text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.04em; }
    main {
      display: grid; grid-template-columns: minmax(0, 1fr) 360px;
      gap: 16px; padding: 16px; max-width: 1480px; margin: 0 auto;
    }
    section {
      background: var(--surface); border: 1px solid var(--line);
      border-radius: 10px; padding: 16px; min-width: 0;
    }
    section + section { margin-top: 16px; }
    .pill {
      display: inline-flex; align-items: center; gap: 6px; min-height: 28px;
      padding: 4px 10px; border: 1px solid var(--line); border-radius: 999px;
      color: var(--muted); background: #11161b; white-space: nowrap; font-size: 12px;
    }
    .lamp { width: 9px; height: 9px; border-radius: 50%; background: var(--red); }
    .pill.good .lamp { background: var(--green); }
    .pill.warn .lamp { background: var(--amber); }

    /* ---------- Faceplate + overlay ---------- */
    .panel-head {
      display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
    }
    .panel-head .sub { color: var(--muted); font-size: 12px; }
    .image-panel {
      position: relative; width: 100%; margin: 0 auto;
      aspect-ratio: 159 / 41.969002; border-radius: 12px; overflow: hidden;
      background: #050607; box-shadow: 0 18px 40px rgba(0,0,0,0.45);
    }
    .image-panel img {
      position: absolute; inset: 0; width: 100%; height: 100%;
      object-fit: contain; user-select: none; pointer-events: none;
    }
    .hotspot {
      position: absolute; padding: 0; border: 1.5px solid transparent;
      border-radius: 7px; background: transparent; color: transparent;
      cursor: pointer;
    }
    .hotspot:hover { border-color: rgba(104,169,255,0.9); background: rgba(104,169,255,0.14); }
    .hotspot:focus-visible { outline: 2px solid var(--blue); outline-offset: 2px; }
    .hotspot.active { border-color: rgba(57,255,91,0.85); background: rgba(57,255,91,0.14); }
    .hotspot.armed { border-color: rgba(255,180,58,0.85); background: rgba(255,180,58,0.12); }

    /* LED dots beside AP / FD / YD keys */
    .panel-led {
      position: absolute; width: 10px; height: 10px; transform: translate(-50%,-50%);
      border-radius: 50%; background: #1c2020; box-shadow: inset 0 0 3px #000;
      pointer-events: none;
    }
    .panel-led.on { background: var(--green); box-shadow: 0 0 10px var(--green); }
    .panel-led.amber-flash { animation: ledAmber 0.6s steps(1) infinite; }
    @keyframes ledAmber {
      0%, 50% { background: var(--amber); box-shadow: 0 0 10px var(--amber); }
      50.01%, 100% { background: #2b2410; box-shadow: inset 0 0 3px #000; }
    }
    .panel-led.ap { left: 3.42%; top: 17.00%; }
    .panel-led.fd { left: 3.42%; top: 50.47%; }
    .panel-led.yd { left: 3.42%; top: 82.94%; }

    /* LCD live annunciations, positioned 1:1 over the SVG display glass */
    .image-lcd {
      position: absolute; left: 15.04%; top: 9.43%; width: 54.55%; height: 51.58%;
      display: grid;
      grid-template-columns: 1fr 1fr 0.85fr 1fr;
      grid-template-rows: 1.35fr 1fr;
      padding: 2.2% 1.6%;
      gap: 0 1.5%;
      font-family: Consolas, "SFMono-Regular", ui-monospace, monospace;
      overflow: hidden; line-height: 1;
    }
    .lcd-cell { min-width: 0; display: flex; flex-direction: column; justify-content: flex-start; }
    .ann { white-space: nowrap; overflow: hidden; text-overflow: clip; text-transform: uppercase; font-weight: 800; }
    .ann-active { color: var(--green); font-size: clamp(15px, 2.7vw, 34px); letter-spacing: 0.02em; }
    .ann-armed  { color: var(--white); font-size: clamp(9px, 1.35vw, 17px); font-weight: 700; margin-top: 6%; }
    .ann-ref    { color: var(--cyan);  font-size: clamp(9px, 1.25vw, 16px); font-weight: 700; white-space: normal; }
    .ann-ref .ref-sub { display: block; margin-top: 4%; color: #9fe7e7; }
    .ann-message {
      color: #d7ead8; font-size: clamp(8px, 1.05vw, 13px); font-weight: 600;
      white-space: pre-line; line-height: 1.25; grid-row: 1 / span 2; align-self: stretch;
    }
    .ann.alert { color: var(--amber); }
    .cell-lat-active { grid-column: 1; grid-row: 1; }
    .cell-lat-armed  { grid-column: 1; grid-row: 2; }
    .cell-vert-active{ grid-column: 2; grid-row: 1; }
    .cell-vert-armed { grid-column: 2; grid-row: 2; }
    .cell-ref        { grid-column: 3; grid-row: 1 / span 2; }
    .cell-msg        { grid-column: 4; grid-row: 1 / span 2; }
    /* Capture flash (inverse video) for ~10s after a mode becomes active */
    .flash-capture { animation: capFlash 0.8s steps(1) infinite; }
    @keyframes capFlash {
      0%, 50% { color: #04140a; background: var(--green); }
      50.01%, 100% { color: var(--green); background: transparent; }
    }

    /* ---------- Controls ---------- */
    * { box-sizing: border-box; }
    button {
      min-height: 38px; border: 1px solid #3b444d; border-radius: 7px;
      background: linear-gradient(180deg, #2d343b, #11161a); color: var(--text);
      font-weight: 650; cursor: pointer;
    }
    button:hover { border-color: var(--blue); }
    button:disabled { opacity: 0.45; cursor: not-allowed; }
    button.primary { border-color: #2f6b3a; background: linear-gradient(180deg, #244e2f, #0f2417); }
    button.warn { border-color: #74312f; background: linear-gradient(180deg, #3a1a19, #170f0e); color: #ffd6d4; }
    .row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
    .row button { min-height: 34px; padding: 0 12px; font-size: 12px; }
    .grid-3 { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 8px; }
    .control-grid {
      display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 10px 12px;
    }
    .control-grid .wide { grid-column: 1 / -1; }
    .control-grid > *, .grid-3 > *, .side-grid > * { min-width: 0; }
    label.field { display: grid; gap: 4px; color: var(--muted); font-size: 12px; }
    input, select {
      width: 100%; min-height: 36px; border: 1px solid #333c44; border-radius: 6px;
      background: #0b0e11; color: var(--text); padding: 0 10px; font-size: 13px;
    }
    .step-field { display: grid; grid-template-columns: 40px minmax(0, 1fr) 40px; gap: 6px; align-items: end; min-width: 0; }
    .step-field label { grid-column: 1 / -1; color: var(--muted); font-size: 12px; margin-bottom: -2px; }
    .step-field button { min-height: 36px; padding: 0; font-size: 18px; }
    .sub-block { border-top: 1px solid var(--line); padding-top: 12px; margin-top: 12px; }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }

    .side-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .metric { background: #10151a; border: 1px solid var(--line); border-radius: 8px; padding: 10px; }
    .metric .label { color: var(--muted); font-size: 12px; margin-bottom: 4px; white-space: nowrap; }
    .metric .value { font-size: 19px; font-weight: 750; overflow-wrap: anywhere; }
    .log { display: flex; flex-direction: column; gap: 6px; color: var(--muted); font-size: 12px; }
    pre {
      margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; color: #c9d1d9;
      font-size: 12px; max-height: 320px; overflow: auto;
    }
    .muted { color: var(--muted); }
    .legend { display: flex; gap: 14px; flex-wrap: wrap; font-size: 11px; color: var(--muted); margin-top: 10px; }
    .legend span { display: inline-flex; align-items: center; gap: 5px; }
    .swatch { width: 11px; height: 11px; border-radius: 3px; display: inline-block; }

    @media (max-width: 1100px) { main { grid-template-columns: 1fr; } }
    @media (max-width: 640px) {
      header { flex-direction: column; align-items: flex-start; }
      .control-grid, .grid-3, .side-grid { grid-template-columns: 1fr; }
      .step-field { grid-template-columns: 36px minmax(0, 1fr) 36px; }
    }
  </style>
</head>
<body>
  <header>
    <h1>GMC 605 MSFS Connector</h1>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <span id="source-pill" class="pill"><span class="lamp"></span><span>Source</span></span>
      <span id="transport-pill" class="pill"><span class="lamp"></span><span>Transport</span></span>
      <span id="rate-pill" class="pill"><span class="lamp"></span><span>Rate</span></span>
    </div>
  </header>
  <main>
    <div>
      <!-- ============ FACEPLATE ============ -->
      <section>
        <div class="panel-head">
          <h2 style="margin:0">GMC 605 Mode Controller</h2>
          <span class="sub">Live annunciations &middot; click a key to send a command</span>
        </div>
        <div class="image-panel">
          <img src="/assets/gmc605_panel.svg" alt="GMC 605 vector faceplate">
          <div class="image-lcd" aria-label="Live GMC 605 annunciations">
            <div class="lcd-cell cell-lat-active"><div id="display-lat-active" class="ann ann-active"></div></div>
            <div class="lcd-cell cell-lat-armed"><div id="display-lat-armed" class="ann ann-armed"></div></div>
            <div class="lcd-cell cell-vert-active"><div id="display-vert-active" class="ann ann-active"></div></div>
            <div class="lcd-cell cell-vert-armed"><div id="display-vert-armed" class="ann ann-armed"></div></div>
            <div class="lcd-cell cell-ref"><div id="display-ref" class="ann ann-ref"></div></div>
            <div class="lcd-cell cell-msg"><div id="display-message" class="ann ann-message">WAITING</div></div>
          </div>
          <span id="panel-led-ap" class="panel-led ap"></span>
          <span id="panel-led-fd" class="panel-led fd"></span>
          <span id="panel-led-yd" class="panel-led yd"></span>
          <button class="hotspot ap-key"  style="left:5.59%;top:8.06%;width:5.97%;height:17.39%"  data-command="AP_PRESS"  aria-label="AP"></button>
          <button class="hotspot fd-key"  style="left:5.59%;top:41.42%;width:5.97%;height:17.39%" data-command="FD_PRESS"  aria-label="FD"></button>
          <button class="hotspot yd-key"  style="left:5.59%;top:74.48%;width:5.97%;height:17.39%" data-command="YD_PRESS"  aria-label="YD"></button>
          <button class="hotspot hdg-key" style="left:16.07%;top:74.48%;width:5.97%;height:17.39%" data-command="HDG_PRESS" aria-label="HDG"></button>
          <button class="hotspot nav-key" style="left:26.34%;top:74.48%;width:5.97%;height:17.39%" data-command="NAV_PRESS" aria-label="NAV"></button>
          <button class="hotspot apr-key" style="left:36.72%;top:74.48%;width:5.97%;height:17.39%" data-command="APR_PRESS" aria-label="APR"></button>
          <button class="hotspot bc-key"  style="left:47.25%;top:74.48%;width:5.97%;height:17.39%" data-command="BC_PRESS"  aria-label="BC"></button>
          <button class="hotspot vnv-key" style="left:58.42%;top:74.48%;width:5.97%;height:17.39%" data-command="VNV_PRESS" aria-label="VNV"></button>
          <button class="hotspot ias-key" style="left:68.72%;top:74.48%;width:5.97%;height:17.39%" data-command="IAS_PRESS" aria-label="IAS"></button>
          <button class="hotspot vs-key"  style="left:79.17%;top:74.48%;width:5.97%;height:17.39%" data-command="VS_PRESS"  aria-label="VS"></button>
          <button class="hotspot alt-key" style="left:79.17%;top:41.12%;width:5.97%;height:17.39%" data-command="ALT_PRESS" aria-label="ALT"></button>
          <button class="hotspot lvl-key" style="left:79.17%;top:8.06%;width:5.97%;height:17.39%"  data-command="LVL_PRESS" aria-label="LVL"></button>
          <button class="hotspot nose-dn" style="left:86.2%;top:18.0%;width:6.5%;height:22.0%" data-step="VS_SET" data-delta="-100" aria-label="Nose down"></button>
          <button class="hotspot nose-up" style="left:86.2%;top:60.0%;width:6.5%;height:22.0%" data-step="VS_SET" data-delta="100"  aria-label="Nose up"></button>
        </div>
        <div class="legend">
          <span><span class="swatch" style="background:var(--green)"></span>Active mode</span>
          <span><span class="swatch" style="background:var(--white)"></span>Armed mode</span>
          <span><span class="swatch" style="background:var(--cyan)"></span>Reference</span>
          <span><span class="swatch" style="background:var(--amber)"></span>Attention / disconnect</span>
        </div>
      </section>

      <!-- ============ GMC 605 CONTROLLER ============ -->
      <section>
        <h2>GMC 605 Controller</h2>
        <p class="muted" style="margin-top:-6px;margin-bottom:12px;font-size:12px">
          Drives the autopilot display state sent to the ESP32: engagement, mode annunciations and pilot-selected references.
        </p>
        <div class="row">
          <button data-preset="climb">Climb</button>
          <button data-preset="cruise">Cruise</button>
          <button data-preset="ils">ILS</button>
          <button data-preset="off" class="warn">Clear FD</button>
        </div>

        <div class="sub-block">
          <h3>Engagement</h3>
          <div class="control-grid">
            <label class="field"><span>AP</span><select id="ap-control"><option value="false">off</option><option value="true">on</option></select></label>
            <label class="field"><span>FD</span><select id="fd-control"><option value="false">off</option><option value="true">on</option></select></label>
            <label class="field"><span>YD</span><select id="yd-control"><option value="false">off</option><option value="true">on</option></select></label>
            <label class="field"><span>Messages (csv, max 4)</span><input id="messages-control" placeholder="DEBUG, LINK"></label>
          </div>
        </div>

        <div class="sub-block">
          <h3>Mode Annunciations</h3>
          <div class="control-grid">
            <label class="field"><span>Lateral active</span><select id="lat-active-control"></select></label>
            <label class="field"><span>Lateral armed</span><select id="lat-armed-control"></select></label>
            <label class="field"><span>Vertical active</span><select id="vert-active-control"></select></label>
            <label class="field"><span>ALT armed</span><select id="arm-alts-control"><option value="">none</option><option>ALT</option><option>ALTS</option></select></label>
            <label class="field"><span>VNAV armed</span><select id="arm-vnav-control"><option value="">none</option><option>VPTH</option><option>ALTV</option></select></label>
            <label class="field"><span>Approach armed</span><select id="arm-approach-control"><option value="">none</option><option>GP</option><option>GS</option></select></label>
          </div>
        </div>

        <div class="sub-block">
          <h3>Selected References (pilot set)</h3>
          <div class="control-grid">
            <div class="step-field"><label>Heading (deg)</label><button data-snap-step="refHeading" data-delta="-1">-</button><input id="ref-heading-control" type="number" min="0" max="359" step="1"><button data-snap-step="refHeading" data-delta="1">+</button></div>
            <div class="step-field"><label>Altitude (ft)</label><button data-snap-step="refAltitude" data-delta="-100">-</button><input id="ref-altitude-control" type="number" step="100"><button data-snap-step="refAltitude" data-delta="100">+</button></div>
            <div class="step-field"><label>Vertical speed (fpm)</label><button data-snap-step="refVs" data-delta="-100">-</button><input id="ref-vs-control" type="number" step="100"><button data-snap-step="refVs" data-delta="100">+</button></div>
            <div class="step-field"><label>Airspeed (kt)</label><button data-snap-step="refSpeed" data-delta="-1">-</button><input id="ref-speed-control" type="number" min="0" step="1"><button data-snap-step="refSpeed" data-delta="1">+</button></div>
          </div>
        </div>

        <div class="actions">
          <button data-apply-snapshot class="primary">Apply To ESP32</button>
          <button data-command="DEBUG_CAPTURE_LATERAL">Capture Lateral</button>
          <button data-command="DEBUG_CAPTURE_VERTICAL">Capture Vertical</button>
          <button data-command="DEBUG_RESET" class="warn">Reset</button>
        </div>
      </section>

      <!-- ============ SIM / AIRCRAFT STATE ============ -->
      <section>
        <h2>Sim / Aircraft State</h2>
        <p class="muted" style="margin-top:-6px;margin-bottom:12px;font-size:12px">
          The simulated aircraft and navigation data feeding the unit. In MSFS mode these come from SimConnect; here you can drive them by hand.
        </p>

        <div class="sub-block">
          <h3>Navigation Source</h3>
          <div class="row">
            <button data-quick-nav="GPS">GPS</button>
            <button data-quick-nav="LOC">LOC / ILS</button>
            <button data-quick-nav="VOR">VOR / VAPP</button>
            <button data-quick-nav="NONE">No NAV</button>
          </div>
          <div class="control-grid">
            <label class="field"><span>SIM connected</span><select id="sim-connected-control"><option value="true">true</option><option value="false">false</option></select></label>
            <label class="field"><span>NAV source</span><select id="nav-source-control"><option>NONE</option><option>GPS</option><option>VOR</option><option>LOC</option></select></label>
          </div>
        </div>

        <div class="sub-block">
          <h3>Aircraft Data</h3>
          <div class="control-grid">
            <div class="step-field"><label>Heading (deg)</label><button data-snap-step="airHeading" data-delta="-5">-</button><input id="air-heading-control" type="number" min="0" max="359" step="1"><button data-snap-step="airHeading" data-delta="5">+</button></div>
            <div class="step-field"><label>Altitude (ft)</label><button data-snap-step="airAltitude" data-delta="-100">-</button><input id="air-altitude-control" type="number" step="100"><button data-snap-step="airAltitude" data-delta="100">+</button></div>
            <div class="step-field"><label>Vertical speed (fpm)</label><button data-snap-step="airVs" data-delta="-100">-</button><input id="air-vs-control" type="number" step="100"><button data-snap-step="airVs" data-delta="100">+</button></div>
            <div class="step-field"><label>Airspeed (kt)</label><button data-snap-step="airSpeed" data-delta="-5">-</button><input id="air-speed-control" type="number" min="0" step="1"><button data-snap-step="airSpeed" data-delta="5">+</button></div>
          </div>
        </div>

        <div class="sub-block">
          <h3>Deviation Needles</h3>
          <div class="control-grid">
            <label class="field"><span>CDI valid</span><select id="cdi-valid-control"><option value="true">true</option><option value="false">false</option></select></label>
            <div class="step-field"><label>CDI needle</label><button data-snap-step="cdi" data-delta="-10">-</button><input id="cdi-needle-control" type="number" min="-127" max="127" step="1"><button data-snap-step="cdi" data-delta="10">+</button></div>
            <label class="field"><span>GSI valid</span><select id="gsi-valid-control"><option value="true">true</option><option value="false">false</option></select></label>
            <div class="step-field"><label>GSI needle</label><button data-snap-step="gsi" data-delta="-10">-</button><input id="gsi-needle-control" type="number" min="-127" max="127" step="1"><button data-snap-step="gsi" data-delta="10">+</button></div>
          </div>
        </div>

        <div class="actions">
          <button data-apply-snapshot class="primary">Apply To ESP32</button>
          <button data-command="DEBUG_RESET" class="warn">Reset Sim State</button>
        </div>
      </section>
    </div>

    <!-- ============ RIGHT RAIL ============ -->
    <div>
      <section>
        <h2>Live State</h2>
        <div class="side-grid">
          <div class="metric"><div class="label">AP</div><div id="ap" class="value">--</div></div>
          <div class="metric"><div class="label">FD</div><div id="fd" class="value">--</div></div>
          <div class="metric"><div class="label">YD</div><div id="yd" class="value">--</div></div>
          <div class="metric"><div class="label">NAV Source</div><div id="nav-source" class="value">--</div></div>
          <div class="metric"><div class="label">CDI / GSI</div><div id="deviation-summary" class="value">--</div></div>
          <div class="metric"><div class="label">Heading Bug</div><div id="ref-heading" class="value">--</div></div>
          <div class="metric"><div class="label">Selected Alt</div><div id="ref-altitude" class="value">--</div></div>
          <div class="metric"><div class="label">Selected VS</div><div id="ref-vs" class="value">--</div></div>
          <div class="metric"><div class="label">Selected Speed</div><div id="ref-speed" class="value">--</div></div>
          <div class="metric"><div class="label">Airspeed</div><div id="air-speed" class="value">--</div></div>
        </div>
      </section>
      <section>
        <h2>Connector Log</h2>
        <div id="log" class="log"></div>
      </section>
      <section>
        <h2>Raw Snapshot</h2>
        <pre id="raw">{}</pre>
      </section>
    </div>
  </main>
  <script>
    const $ = (id) => document.getElementById(id);
    let lastStatus = null;
    const lateralModes = ["NONE", "ROL", "HDG", "GPS", "VOR", "LOC", "VAPP", "BC", "LVL", "GA"];
    const verticalModes = ["NONE", "PIT", "ALT", "ALTS", "VS", "IAS", "FLC", "VPTH", "ALTV", "GP", "GS", "LVL", "GA"];

    // ----- real display-rule state tracking -----
    const prev = { lat_active: null, vert_active: null, ap: null, yd: null };
    const flashUntil = { latActive: 0, vertActive: 0 };
    const ledFlashUntil = { ap: 0, fd: 0, yd: 0 };
    const CAPTURE_FLASH_MS = 10000;  // mode capture flashes ~10s
    const DISCONNECT_FLASH_MS = 5000; // AP/YD disconnect flashes ~5s

    function createControls() {
      if (document.body.dataset.controlsReady) return;
      document.body.dataset.controlsReady = "true";

      fillSelect("lat-active-control", lateralModes);
      fillSelect("lat-armed-control", lateralModes);
      fillSelect("vert-active-control", verticalModes);

      document.querySelectorAll("[data-command]").forEach((button) => {
        button.addEventListener("click", () => sendCommand(button.dataset.command));
      });
      document.querySelectorAll("[data-step]").forEach((button) => {
        button.addEventListener("click", () => {
          const command = button.dataset.step;
          const delta = Number(button.dataset.delta || 0);
          const snapshot = lastStatus && lastStatus.snapshot;
          if (!snapshot) return;
          sendCommand(command, (snapshot.references.vs_fpm || 0) + delta);
        });
      });
      document.querySelectorAll("[data-apply-snapshot]").forEach((button) => {
        button.addEventListener("click", () => sendCommand("DEBUG_SET_SNAPSHOT", snapshotFormValue()));
      });
      document.querySelectorAll("[data-preset]").forEach((button) => {
        button.addEventListener("click", () => applyPreset(button.dataset.preset));
      });
      document.querySelectorAll("[data-snap-step]").forEach((button) => {
        button.addEventListener("click", () => stepSnapshotField(button.dataset.snapStep, Number(button.dataset.delta || 0)));
      });
      document.querySelectorAll("[data-quick-nav]").forEach((button) => {
        button.addEventListener("click", () => setNavPreset(button.dataset.quickNav));
      });
    }

    function fillSelect(id, values) {
      const select = $(id);
      select.replaceChildren(...values.map((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        return option;
      }));
    }

    async function sendCommand(command, value = null) {
      const body = value === null ? { command } : { command, value };
      await fetch("/api/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      await refresh();
    }

    function setPill(id, ok, text, warn = false) {
      const node = $(id);
      node.className = "pill " + (ok ? "good" : warn ? "warn" : "");
      node.lastElementChild.textContent = text;
    }

    function onOff(value) { return value ? "ON" : "OFF"; }
    function modeValue(value) { return value && value.length ? value : "NONE"; }
    function panelModeValue(value) { return value && value !== "NONE" ? value : ""; }
    function validNeedle(dev) { return dev && dev.valid ? `${dev.needle}` : "INVALID"; }
    function armedText(value) {
      if (Array.isArray(value)) return value.length ? value.map(panelModeValue).filter(Boolean).join(" ") : "";
      return panelModeValue(value);
    }
    function referenceHtml(snapshot) {
      const r = snapshot.references;
      const mode = snapshot.vert_active;
      if (mode === "VS") return `<span>${r.vs_fpm > 0 ? "+" : ""}${r.vs_fpm}</span><span class="ref-sub">FPM</span>`;
      if (mode === "IAS" || mode === "FLC") return `<span>${r.speed_kt}</span><span class="ref-sub">KT</span>`;
      if (mode === "ALT" || mode === "ALTS" || mode === "ALTV") return `<span>${r.altitude_ft}</span><span class="ref-sub">FT</span>`;
      if (!snapshot.fd) return "";
      return `<span>${r.altitude_ft}</span><span class="ref-sub">FT</span>`;
    }
    function messageText(snapshot) {
      if (!snapshot.sim_connected) return "NO SIM";
      if (snapshot.messages && snapshot.messages.length) return snapshot.messages.slice(0, 4).join("\n");
      return "";
    }
    function boolValue(id) { return $(id).value === "true"; }
    function numberValue(id) { return Number($(id).value || 0); }
    function setValue(id, value) {
      const node = $(id);
      if (document.activeElement !== node) node.value = String(value);
    }
    function setBool(id, value) { setValue(id, value ? "true" : "false"); }
    function setCsv(id, values) { setValue(id, (values || []).join(", ")); }
    function fieldNumber(id) { return Number($(id).value || 0); }
    function stepSnapshotField(field, delta) {
      const fields = {
        refHeading: ["ref-heading-control", 360],
        refAltitude: ["ref-altitude-control", null],
        refVs: ["ref-vs-control", null],
        refSpeed: ["ref-speed-control", null],
        airHeading: ["air-heading-control", 360],
        airAltitude: ["air-altitude-control", null],
        airVs: ["air-vs-control", null],
        airSpeed: ["air-speed-control", null],
        cdi: ["cdi-needle-control", null],
        gsi: ["gsi-needle-control", null],
      };
      const config = fields[field];
      if (!config) return;
      let next = fieldNumber(config[0]) + delta;
      if (config[1]) next = ((next % config[1]) + config[1]) % config[1];
      if (field === "refSpeed" || field === "airSpeed") next = Math.max(0, next);
      if (field === "cdi" || field === "gsi") next = Math.max(-127, Math.min(127, next));
      $(config[0]).value = String(next);
      sendCommand("DEBUG_SET_SNAPSHOT", snapshotFormValue());
    }
    function setNavPreset(source) {
      $("nav-source-control").value = source;
      if (source === "GPS") {
        $("lat-active-control").value = "GPS"; $("lat-armed-control").value = "NONE"; $("arm-approach-control").value = "GP";
      } else if (source === "LOC") {
        $("lat-active-control").value = "HDG"; $("lat-armed-control").value = "LOC"; $("arm-approach-control").value = "GS";
      } else if (source === "VOR") {
        $("lat-active-control").value = "HDG"; $("lat-armed-control").value = "VAPP"; $("arm-approach-control").value = "";
      } else {
        $("lat-active-control").value = "ROL"; $("lat-armed-control").value = "NONE"; $("arm-approach-control").value = "";
      }
      sendCommand("DEBUG_SET_SNAPSHOT", snapshotFormValue());
    }
    function applyPreset(name) {
      const presets = {
        climb: {
          nav_source: "GPS", lat_active: "GPS", lat_armed: "NONE",
          vert_active: "FLC", vert_armed: ["ALTS"], ap: true, fd: true, yd: true,
          references: { heading_deg: 90, altitude_ft: 8000, vs_fpm: 700, speed_kt: 120 },
          aircraft: { heading_deg: 90, altitude_ft: 3500, vs_fpm: 700, airspeed_kt: 120 },
          cdi: { valid: true, needle: 0 }, gsi: { valid: false, needle: 0 }, messages: ["DEBUG"]
        },
        cruise: {
          nav_source: "GPS", lat_active: "GPS", lat_armed: "NONE",
          vert_active: "ALT", vert_armed: [], ap: true, fd: true, yd: true,
          references: { heading_deg: 90, altitude_ft: 8000, vs_fpm: 0, speed_kt: 140 },
          aircraft: { heading_deg: 90, altitude_ft: 8000, vs_fpm: 0, airspeed_kt: 140 },
          cdi: { valid: true, needle: 0 }, gsi: { valid: false, needle: 0 }, messages: ["DEBUG"]
        },
        ils: {
          nav_source: "LOC", lat_active: "LOC", lat_armed: "NONE",
          vert_active: "PIT", vert_armed: ["GS", "ALTS"], ap: true, fd: true, yd: true,
          references: { heading_deg: 273, altitude_ft: 3000, vs_fpm: -500, speed_kt: 110 },
          aircraft: { heading_deg: 273, altitude_ft: 3200, vs_fpm: -300, airspeed_kt: 115 },
          cdi: { valid: true, needle: 10 }, gsi: { valid: true, needle: -15 }, messages: ["DEBUG"]
        },
        off: {
          nav_source: "NONE", lat_active: "NONE", lat_armed: "NONE",
          vert_active: "NONE", vert_armed: [], ap: false, fd: false, yd: false,
          references: { heading_deg: 0, altitude_ft: 0, vs_fpm: 0, speed_kt: 0 },
          aircraft: { heading_deg: 0, altitude_ft: 0, vs_fpm: 0, airspeed_kt: 0 },
          cdi: { valid: false, needle: 0 }, gsi: { valid: false, needle: 0 }, messages: ["DEBUG"]
        }
      };
      const preset = presets[name];
      if (preset) sendCommand("DEBUG_SET_SNAPSHOT", preset);
    }
    function snapshotFormValue() {
      const vertArmed = [
        $("arm-alts-control").value,
        $("arm-vnav-control").value,
        $("arm-approach-control").value,
      ].filter(Boolean);
      return {
        sim_connected: boolValue("sim-connected-control"),
        ap: boolValue("ap-control"),
        fd: boolValue("fd-control"),
        yd: boolValue("yd-control"),
        nav_source: $("nav-source-control").value,
        lat_active: $("lat-active-control").value,
        lat_armed: $("lat-armed-control").value,
        vert_active: $("vert-active-control").value,
        vert_armed: vertArmed,
        references: {
          heading_deg: numberValue("ref-heading-control"),
          altitude_ft: numberValue("ref-altitude-control"),
          vs_fpm: numberValue("ref-vs-control"),
          speed_kt: numberValue("ref-speed-control"),
        },
        aircraft: {
          heading_deg: numberValue("air-heading-control"),
          altitude_ft: numberValue("air-altitude-control"),
          vs_fpm: numberValue("air-vs-control"),
          airspeed_kt: numberValue("air-speed-control"),
        },
        cdi: { valid: boolValue("cdi-valid-control"), needle: numberValue("cdi-needle-control") },
        gsi: { valid: boolValue("gsi-valid-control"), needle: numberValue("gsi-needle-control") },
        messages: $("messages-control").value.split(",").map((v) => v.trim().toUpperCase()).filter(Boolean).slice(0, 4),
      };
    }
    function updateSnapshotControls(s) {
      setBool("sim-connected-control", s.sim_connected);
      setBool("ap-control", s.ap);
      setBool("fd-control", s.fd);
      setBool("yd-control", s.yd);
      setValue("nav-source-control", s.nav_source);
      setValue("lat-active-control", s.lat_active);
      setValue("lat-armed-control", s.lat_armed);
      setValue("vert-active-control", s.vert_active);
      setValue("arm-alts-control", (s.vert_armed || []).find((m) => m === "ALT" || m === "ALTS") || "");
      setValue("arm-vnav-control", (s.vert_armed || []).find((m) => m === "VPTH" || m === "ALTV") || "");
      setValue("arm-approach-control", (s.vert_armed || []).find((m) => m === "GP" || m === "GS") || "");
      setCsv("messages-control", s.messages);
      setValue("ref-heading-control", s.references.heading_deg);
      setValue("ref-altitude-control", s.references.altitude_ft);
      setValue("ref-vs-control", s.references.vs_fpm);
      setValue("ref-speed-control", s.references.speed_kt);
      setValue("air-heading-control", s.aircraft.heading_deg);
      setValue("air-altitude-control", s.aircraft.altitude_ft);
      setValue("air-vs-control", s.aircraft.vs_fpm);
      setValue("air-speed-control", s.aircraft.airspeed_kt);
      setBool("cdi-valid-control", s.cdi.valid);
      setValue("cdi-needle-control", s.cdi.needle);
      setBool("gsi-valid-control", s.gsi.valid);
      setValue("gsi-needle-control", s.gsi.needle);
    }

    function setKeyState(command, state) {
      document.querySelectorAll(`[data-command="${command}"]`).forEach((node) => {
        node.classList.remove("active", "armed");
        if (state) node.classList.add(state);
      });
    }
    function clearKeyStates() {
      document.querySelectorAll(".hotspot").forEach((node) => node.classList.remove("active", "armed"));
    }

    // Detect captures/disconnects to drive real display-rule flashing.
    function trackDisplayRules(s) {
      const now = Date.now();
      const latA = panelModeValue(s.lat_active);
      const vertA = panelModeValue(s.vert_active);
      const steady = new Set(["", "ROL", "PIT"]);
      if (prev.lat_active !== null && latA !== prev.lat_active && !steady.has(latA)) flashUntil.latActive = now + CAPTURE_FLASH_MS;
      if (prev.vert_active !== null && vertA !== prev.vert_active && !steady.has(vertA)) flashUntil.vertActive = now + CAPTURE_FLASH_MS;
      if (prev.ap === true && s.ap === false) ledFlashUntil.ap = now + DISCONNECT_FLASH_MS;
      if (prev.yd === true && s.yd === false) ledFlashUntil.yd = now + DISCONNECT_FLASH_MS;
      prev.lat_active = latA; prev.vert_active = vertA; prev.ap = s.ap; prev.yd = s.yd;
    }

    function render(status) {
      lastStatus = status;
      createControls();
      const s = status.snapshot;
      setPill("source-pill", status.source_open, `${status.source.toUpperCase()} source`);
      setPill("transport-pill", status.transport_open, status.transport_enabled ? "UART transport" : "No UART", !status.transport_enabled);
      setPill("rate-pill", true, `${status.update_hz} Hz`);

      document.querySelectorAll("button").forEach((button) => button.disabled = !status.source_open);
      if (!s) { $("raw").textContent = JSON.stringify(status, null, 2); return; }

      trackDisplayRules(s);
      const now = Date.now();

      clearKeyStates();
      $("panel-led-ap").classList.toggle("on", Boolean(s.ap));
      $("panel-led-fd").classList.toggle("on", Boolean(s.fd));
      $("panel-led-yd").classList.toggle("on", Boolean(s.yd));
      $("panel-led-ap").classList.toggle("amber-flash", now < ledFlashUntil.ap);
      $("panel-led-yd").classList.toggle("amber-flash", now < ledFlashUntil.yd);

      setKeyState("AP_PRESS", s.ap ? "active" : "");
      setKeyState("FD_PRESS", s.fd ? "active" : "");
      setKeyState("YD_PRESS", s.yd ? "active" : "");
      const latActiveCommand = { HDG: "HDG_PRESS", GPS: "NAV_PRESS", VOR: "NAV_PRESS", LOC: "NAV_PRESS", VAPP: "APR_PRESS", BC: "BC_PRESS", LVL: "LVL_PRESS", GA: "GA_PRESS" }[s.lat_active];
      const latArmedCommand = { GPS: "NAV_PRESS", VOR: "NAV_PRESS", LOC: "NAV_PRESS", VAPP: "APR_PRESS", BC: "BC_PRESS" }[s.lat_armed];
      const vertActiveCommand = { ALT: "ALT_PRESS", VS: "VS_PRESS", IAS: "IAS_PRESS", FLC: "FLC_PRESS", VPTH: "VNV_PRESS", LVL: "LVL_PRESS", GA: "GA_PRESS" }[s.vert_active];
      if (latActiveCommand) setKeyState(latActiveCommand, "active");
      if (latArmedCommand && latArmedCommand !== latActiveCommand) setKeyState(latArmedCommand, "armed");
      if (vertActiveCommand) setKeyState(vertActiveCommand, "active");
      if (s.vert_armed && s.vert_armed.includes("VPTH")) setKeyState("VNV_PRESS", "armed");
      if (s.vert_armed && (s.vert_armed.includes("GP") || s.vert_armed.includes("GS"))) setKeyState("APR_PRESS", "armed");
      if (s.vert_armed && (s.vert_armed.includes("ALT") || s.vert_armed.includes("ALTS"))) setKeyState("ALT_PRESS", "armed");

      const latActive = $("display-lat-active");
      const vertActive = $("display-vert-active");
      latActive.textContent = panelModeValue(s.lat_active);
      vertActive.textContent = panelModeValue(s.vert_active);
      latActive.classList.toggle("flash-capture", now < flashUntil.latActive && Boolean(latActive.textContent));
      vertActive.classList.toggle("flash-capture", now < flashUntil.vertActive && Boolean(vertActive.textContent));
      $("display-lat-armed").textContent = armedText(s.lat_armed);
      $("display-vert-armed").textContent = armedText(s.vert_armed);
      const msg = messageText(s);
      const msgNode = $("display-message");
      msgNode.textContent = msg;
      msgNode.classList.toggle("alert", /FAIL|NO SIM|LINK|DISABLD/.test(msg));
      $("display-ref").innerHTML = referenceHtml(s);

      $("ap").textContent = onOff(s.ap);
      $("fd").textContent = onOff(s.fd);
      $("yd").textContent = onOff(s.yd);
      $("nav-source").textContent = modeValue(s.nav_source);
      $("deviation-summary").textContent = `C ${validNeedle(s.cdi)} / G ${validNeedle(s.gsi)}`;
      $("ref-heading").textContent = `${s.references.heading_deg} deg`;
      $("ref-altitude").textContent = `${s.references.altitude_ft} ft`;
      $("ref-vs").textContent = `${s.references.vs_fpm} fpm`;
      $("ref-speed").textContent = `${s.references.speed_kt} kt`;
      $("air-speed").textContent = `${s.aircraft.airspeed_kt} kt`;
      updateSnapshotControls(s);
      $("log").replaceChildren(...(status.log.length ? status.log : ["No events yet."]).map((line) => {
        const node = document.createElement("div");
        node.textContent = line;
        return node;
      }));
      $("raw").textContent = JSON.stringify(s, null, 2);
    }

    async function refresh() {
      try {
        const response = await fetch("/api/status", { cache: "no-store" });
        render(await response.json());
      } catch (error) {
        if (!lastStatus) $("raw").textContent = String(error);
      }
    }

    refresh();
    setInterval(refresh, 500);
  </script>
</body>
</html>
"""
