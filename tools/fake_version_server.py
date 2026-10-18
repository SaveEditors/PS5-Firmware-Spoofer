#!/usr/bin/env python3
"""Aniketos live fake-version server (PC side).

Run this on the PC:

    python fake_version_server.py

Then:

  1. Open http://<PC-IP>:8909/ in any browser on the same network
     (the startup banner prints the exact URL).
  2. Type the version text to show on the PS5 and press "Set".
  3. The console picks it up within ~3 seconds (it polls /value).
     Open Settings > System > System Information to see it.

The console only polls when the patched shellui module was built with
--live-url http://<PC-IP>:8909/value; the startup banner prints the exact
rebuild command with this PC's LAN IP.

Endpoints:
  GET  /        small page with the current value and an input box
  GET  /value   text/plain current value   <- this is what the console polls
  GET  /json    {"value": "..."}
  POST /set     form field 'value' (or raw text body) -> sets the value

The value is persisted next to this script in live_version.txt.
"""

import argparse
import json
import os
import socket
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, "live_version.txt")
DEFAULT_VALUE = "9.99"
MAX_LEN = 200

_lock = threading.Lock()
_value = DEFAULT_VALUE


def load_value():
    global _value
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            v = f.read().strip()
            if v:
                _value = v[:MAX_LEN]
    except OSError:
        pass


def save_value(v):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(v)
    except OSError:
        pass


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Aniketos fake version</title>
<style>
 body {{ font-family: Segoe UI, Arial, sans-serif; margin: 40px; background: #101216; color: #e8e8e8; }}
 h1 {{ font-size: 20px; }}
 .box {{ background: #1b1f27; padding: 20px; border-radius: 10px; max-width: 520px; }}
 .now {{ font-size: 26px; font-weight: 600; color: #7ee787; margin: 10px 0 18px; }}
 input[type=text] {{ width: 320px; padding: 8px; font-size: 16px; border-radius: 6px; border: 1px solid #444; background: #0d0f13; color: #fff; }}
 button {{ padding: 9px 18px; font-size: 16px; border-radius: 6px; border: 0; background: #2f81f7; color: #fff; cursor: pointer; }}
 button:hover {{ background: #4493f8; }}
 .hint {{ color: #9aa4b2; font-size: 13px; margin-top: 14px; line-height: 1.5; }}
 code {{ background: #0d0f13; padding: 2px 6px; border-radius: 4px; }}
</style></head><body>
 <div class="box">
  <h1>PS5 fake version</h1>
  <div>Currently served: <span class="now" id="now">{value}</span></div>
  <form method="post" action="/set">
   <input type="text" name="value" id="value" value="{value}" maxlength="{maxlen}" autofocus>
   <button type="submit">Set</button>
  </form>
  <div class="hint">
   The console polls <code>/value</code> every 2.5&nbsp;s. Set a new value here,
   then open <b>Settings &gt; System &gt; System Information</b> on the PS5.<br>
   This is a display-only spoof; the real firmware version never changes.
  </div>
 </div>
 <script>
  // keep the shown value in sync if another browser changes it
  setInterval(function () {{
    fetch('/value').then(function (r) {{ return r.text(); }}).then(function (t) {{
      document.getElementById('now').textContent = t;
    }}).catch(function () {{}});
  }}, 2000);
 </script>
</body></html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "AniketosVersion/1.0"

    def _send(self, code, body, ctype="text/plain; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        with _lock:
            value = _value
        if path in ("/", "/index.html"):
            page = PAGE.format(value=escape_html(value), maxlen=MAX_LEN)
            self._send(200, page, "text/html; charset=utf-8")
        elif path == "/value":
            self._send(200, value)
        elif path == "/json":
            self._send(200, json.dumps({"value": value}), "application/json")
        elif path == "/favicon.ico":
            self._send(204, b"")
        else:
            self._send(404, "not found\n")

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip()
        value = None
        if ctype == "application/x-www-form-urlencoded":
            form = urllib.parse.parse_qs(raw.decode("utf-8", "replace"))
            if "value" in form:
                value = form["value"][0]
            elif raw and b"=" not in raw:
                # tolerate `curl -d 8.88` (curl defaults to the form type)
                value = raw.decode("utf-8", "replace")
        else:
            value = raw.decode("utf-8", "replace")
        if path != "/set":
            self._send(404, "not found\n")
            return
        if value is None or not value.strip():
            self._send(400, "missing value\n")
            return
        global _value
        with _lock:
            _value = value.strip()[:MAX_LEN]
            save_value(_value)
        if ctype == "application/x-www-form-urlencoded":
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
        else:
            self._send(200, _value + "\n")

    def log_message(self, fmt, *args):
        sys.stdout.write("  %s - %s\n" % (self.address_string(), fmt % args))


def escape_html(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def lan_ips():
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
        finally:
            s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except OSError:
        pass
    return ips or ["<PC-IP>"]


def main():
    ap = argparse.ArgumentParser(description="Aniketos live fake-version server")
    ap.add_argument("--port", type=int, default=8909)
    ap.add_argument("--bind", default="0.0.0.0")
    ap.add_argument("--value", default=None, help="initial value (default: last one / 9.99)")
    args = ap.parse_args()

    load_value()
    if args.value is not None:
        global _value
        _value = args.value.strip()[:MAX_LEN]
        save_value(_value)

    ips = lan_ips()
    print("Aniketos live fake-version server")
    print("  serving value: %r" % _value)
    print("  open in a PC browser:  http://%s:%d/" % (ips[0], args.port))
    print()
    print("  console URL for the patched shellui build:")
    print("    --live-url http://%s:%d/value" % (ips[0], args.port))
    print("  full rebuild command (run from the repo root):")
    print("    python tools\\apply_mod.py --version %s --live-url http://%s:%d/value"
          % (_value, ips[0], args.port))
    print()
    print("  note: allow this program through the Windows firewall (private networks)")
    print("  stop with Ctrl+C")
    server = ThreadingHTTPServer((args.bind, args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
