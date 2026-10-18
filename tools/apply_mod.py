#!/usr/bin/env python3
"""apply_mod.py - AniketosHEN shellui patch builder (PS5 FW 12.60).

Builds a modded embedded_000d88c0.elf (shellui module) from the stock file:

  * 4 byte-level edits ("Option E") that let the SETTINGS app receive the
    Aniketos JS injection, while home injection and everything else stays
    exactly as stock. All edits are same-size; the file keeps its length.
  * Replaces the 7954-byte injected payload script with the new one:
    original home patches + System Information version spoof + optional
    live value poll (settings only).

Optionally splices the patched module back into outer.elf (stage2.elf) at
0xd88c0 (same-size splice), producing a drop-in replacement.

Everything is checked:
  * stock SHA-256 + size (warning only: the offsets were written for one
    build, a different file is warned about and still tried)
  * patch-site stock bytes (stops when the expected code is not there)
  * payload fits the 7954-byte budget, is pure ASCII, has no NUL bytes
  * payload syntax checked with `node --check` when node is available
  * final byte-diff report: the output differs from stock ONLY at the
    listed patch sites + the payload region

Usage:
  python apply_mod.py --version 9.99
  python apply_mod.py --version 9.99 --live-url http://192.168.1.50:8909/value
  python apply_mod.py --stock X.elf --out Y.elf [--stock-outer O.elf --out-outer P.elf]

Defaults are relative to the repo root:
  stock module   <repo>/stock/embedded_000d88c0.elf  (you provide - see stock/README.md)
  stock outer    <repo>/stock/outer.elf              (you provide)
  outputs        <repo>/out/embedded_000d88c0.modded.elf
                 <repo>/out/stage2.modded.elf
                 <repo>/out/payload-built.js   (exact bytes in the ELF)
                 <repo>/out/build-report.txt
"""

import argparse
import hashlib
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------- constants

STOCK_SIZE = 4656944
STOCK_SHA256 = "7b9212552a1f2bcb06bf89bdd83f3308007bd905e87e78d2acde27e0019487e9"

OUTER_SIZE = 28436984
OUTER_SHA256 = "38c3c50ddd4d989f8f168ff56f44113235b71d967ecc8415c10bedfdb076de68"
OUTER_MODULE_OFF = 0xD88C0

PAYLOAD_OFF = 0x296B20
PAYLOAD_BUDGET = 7954  # exact stock payload length (NUL sits at 0x298a32)
NUL_OFF = 0x298A32
DATA_OFF = 0x298A34  # first byte of the data table after the string

# (offset, stock bytes, new bytes, rationale)
PATCHES = [
    (0xE68BC, b"\x72", b"\x73",
     "loop2 memchr char 'r' -> 's' (new needle starts with 's')"),
    (0xE6921, b"\x41\x0f\x95\xc4", b"\x41\xb4\x01\x90",
     "bVar22 forced true (mov r12b,1 + nop replaces setne r12b)"),
    (0x28F6A0, b"rnps-control-cen", b"settings (NPXS40",
     "needle part A @VA 0x38b6a0 (16 bytes)"),
    (0x28F590, b"s-control-center", b"tings (NPXS40008",
     "needle part B @VA 0x38b590 (16 bytes)"),
]

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_STOCK = os.path.join(REPO, "stock", "embedded_000d88c0.elf")
DEFAULT_OUTER = os.path.join(REPO, "stock", "outer.elf")
DEFAULT_OUT_DIR = os.path.join(REPO, "out")
DEFAULT_TEMPLATE = os.path.join(HERE, "payload_template.js")

MAX_VERSION = 64
MAX_LIVE_URL = 160

# ---------------------------------------------------------------- helpers


def die(msg):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(1)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def find_all(data, pat):
    out = []
    i = data.find(pat)
    while i != -1:
        out.append(i)
        i = data.find(pat, i + 1)
    return out


def js_escape(s):
    out = []
    for ch in s:
        o = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == "'":
            out.append("\\'")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif 32 <= o < 127:
            out.append(ch)
        else:
            die("unsupported character %r in value" % ch)
    return "".join(out)


def build_payload(template_text, version, live_url):
    """Returns (exact 7954-byte payload, readable pre-padding text)."""
    text = re.sub(r"/\*.*?\*/", "", template_text, flags=re.S)
    text = "\n".join(ln.strip() for ln in text.splitlines() if ln.strip())
    for token in ("__FAKE_VERSION__", "__LIVE_URL__"):
        if token not in text:
            die("template is missing token " + token)
    if len(version) > MAX_VERSION:
        die("version longer than %d characters" % MAX_VERSION)
    if len(live_url) > MAX_LIVE_URL:
        die("live URL longer than %d characters" % MAX_LIVE_URL)
    text = text.replace("__FAKE_VERSION__", js_escape(version))
    text = text.replace("__LIVE_URL__", js_escape(live_url))
    data = text.encode("ascii")
    if b"\x00" in data:
        die("payload contains NUL bytes")
    if len(data) > PAYLOAD_BUDGET:
        die("payload too big: %d bytes (budget %d)" % (len(data), PAYLOAD_BUDGET))
    padded = data + b" " * (PAYLOAD_BUDGET - len(data))
    return padded, text


def node_check(text):
    node = shutil.which("node")
    if not node:
        print("note: node not found, syntax check skipped")
        return
    fd, path = tempfile.mkstemp(suffix=".js")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(text.encode("utf-8"))
        r = subprocess.run([node, "--check", path],
                           capture_output=True, text=True)
        if r.returncode != 0:
            die("node --check failed:\n" + r.stderr)
        print("node --check: payload syntax OK")
    finally:
        os.unlink(path)


def patch_module(stock, payload, report):
    h = sha256(stock)
    if len(stock) != STOCK_SIZE or h != STOCK_SHA256:
        # the offsets were only tested on one build, so anything else gets a
        # warning instead of an error. the patch-site checks further down are
        # the real safety net: they stop on code that does not look expected.
        hints = []
        for off, old, new, _ in PATCHES:
            if stock[off:off + len(old)] == new:
                hints.append("already patched at 0x%x" % off)
        extra = ("  (" + "; ".join(hints) + ")" if hints else "")
        msg = ("warning: module is not the tested stock build: %d bytes "
               "(expected %d), sha256 %s%s -- offsets only tested on the "
               "expected build, trying anyway" % (len(stock), STOCK_SIZE, h, extra))
        print(msg)
        report.append(msg)
    if len(stock) < DATA_OFF:
        die("module file is smaller than the payload region (%d bytes)" % len(stock))
    report.append("stock module: %d bytes, sha256 %s" % (len(stock), h))

    # extra context assertions around the instruction-level patches
    if stock[0xE68BB:0xE68C0] != b"\xbe\x72\x00\x00\x00":
        die("unexpected bytes before loop2 memchr patch site")
    if stock[0xE6919:0xE6925] != b"\x41\x83\xbd\x44\x06\x00\x00\x00\x41\x0f\x95\xc4":
        die("unexpected bytes around bVar22 patch site")

    # every patch must preserve length (byte-preserving guarantee)
    for off, old, new, _ in PATCHES:
        if len(old) != len(new):
            die("patch at 0x%x changes length (%d -> %d)" % (off, len(old), len(new)))

    # needle constants must be unique in the file (offset safety)
    for off, old in ((0x28F6A0, b"rnps-control-cen"), (0x28F590, b"s-control-center")):
        n = len(find_all(stock, old))
        if n != 1:
            die("stock string %r occurs %d times (expected 1)" % (old, n))

    if stock[NUL_OFF] != 0 or stock[NUL_OFF + 1] != 0:
        die("expected two NUL bytes at 0x%x" % NUL_OFF)

    d = bytearray(stock)
    for off, old, new, why in PATCHES:
        got = bytes(d[off:off + len(old)])
        if got != old:
            die("patch site 0x%x: found %s, expected %s" % (off, got.hex(), old.hex()))
        d[off:off + len(old)] = new
        report.append("patched 0x%06x: %s -> %s   (%s)" % (
            off, show_bytes(old), show_bytes(new), why))

    d[PAYLOAD_OFF:PAYLOAD_OFF + PAYLOAD_BUDGET] = payload
    report.append("payload written at 0x%x (%d bytes, sha256 %s)" % (
        PAYLOAD_OFF, PAYLOAD_BUDGET, sha256(payload)))
    if d[NUL_OFF] != 0 or d[NUL_OFF + 1] != 0:
        die("payload write disturbed the trailing NULs")
    if bytes(d[DATA_OFF:DATA_OFF + 4]) != stock[DATA_OFF:DATA_OFF + 4]:
        die("payload write disturbed the following data table")

    patched = bytes(d)

    # full diff verification: differences only at the expected places
    expected = [(off, off + len(new)) for off, _, new, _ in PATCHES]
    expected.append((PAYLOAD_OFF, PAYLOAD_OFF + PAYLOAD_BUDGET))
    diffs = []
    i = 0
    n = len(stock)
    while i < n:
        if stock[i] != patched[i]:
            j = i
            while j < n and stock[j] != patched[j]:
                j += 1
            diffs.append((i, j))
            i = j
        else:
            i += 1
    for a, b in diffs:
        covered = any(a >= ea and b <= eb for ea, eb in expected)
        if not covered:
            die("unexpected difference at 0x%x..0x%x" % (a, b))
    for off, _, new, _ in PATCHES:
        if patched[off:off + len(new)] != new:
            die("patch at 0x%x did not stick" % off)
    report.append("diff check: %d changed region(s), all within expected sites" % len(diffs))
    return patched


def repack_outer(stock_outer, stock_module, patched_module, report):
    ho = sha256(stock_outer)
    if len(stock_outer) != OUTER_SIZE or ho != OUTER_SHA256:
        msg = ("warning: outer/stage2 is not the tested stock build: %d bytes "
               "(expected %d), sha256 %s -- trying the same splice location "
               "anyway" % (len(stock_outer), OUTER_SIZE, ho))
        print(msg)
        report.append(msg)
    off = OUTER_MODULE_OFF
    end = off + len(stock_module)
    if stock_outer[off:end] != stock_module:
        die("outer.elf region 0x%x does not match the module file, "
            "different stage2 layout" % off)
    modded_end_marker = stock_outer[end:end + 4]
    if modded_end_marker != struct.pack("<I", STOCK_SIZE):
        die("unexpected trailer after shellui module in outer.elf")
    out = bytearray(stock_outer)
    out[off:end] = patched_module
    out = bytes(out)
    if out[end:end + 4] != modded_end_marker:
        die("repack disturbed the trailer")
    # full diff verification vs stock
    diffs = []
    i = 0
    while i < len(out):
        if out[i] != stock_outer[i]:
            j = i
            while j < len(out) and out[j] != stock_outer[j]:
                j += 1
            diffs.append((i, j))
            i = j
        else:
            i += 1
    for a, b in diffs:
        if not (a >= off and b <= end):
            die("repack changed unexpected bytes at 0x%x..0x%x" % (a, b))
    report.append("outer.elf: spliced module at 0x%x (region %d bytes), "
                  "%d changed region(s), all inside the module" % (off, len(patched_module), len(diffs)))
    return out


# ---------------------------------------------------------------- main


def show_bytes(b):
    if all(32 <= x < 127 for x in b):
        return b.decode("ascii")
    return b.hex()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stock", default=DEFAULT_STOCK, help="stock shellui module ELF")
    ap.add_argument("--out", default=os.path.join(DEFAULT_OUT_DIR, "embedded_000d88c0.modded.elf"),
                    help="patched module output path")
    ap.add_argument("--stock-outer", default=DEFAULT_OUTER, help="stock outer/stage2 ELF")
    ap.add_argument("--out-outer", default=os.path.join(DEFAULT_OUT_DIR, "stage2.modded.elf"),
                    help="repacked outer/stage2 output path")
    ap.add_argument("--template", default=DEFAULT_TEMPLATE, help="payload template (tools/payload_template.js)")
    ap.add_argument("--version", default="9.99", help="fake displayVersion (default 9.99)")
    ap.add_argument("--live-url", default="",
                    help="optional PC URL polled for a live version, e.g. http://192.168.1.50:8909/value")
    ap.add_argument("--payload-out", default="",
                    help="where to save the exact payload JS (default: payload-built.js next to --out)")
    ap.add_argument("--skip-outer", action="store_true", help="only build the module")
    args = ap.parse_args()

    report = []
    print("== AniketosHEN shellui patch builder ==")
    with open(args.template, "r", encoding="utf-8") as f:
        template_text = f.read()
    payload, payload_text = build_payload(template_text, args.version, args.live_url)
    print("payload: %d bytes of code, padded to %d (headroom %d), version=%r live=%r" % (
        len(payload_text.encode("ascii")), PAYLOAD_BUDGET,
        PAYLOAD_BUDGET - len(payload_text.encode("ascii")), args.version, args.live_url))
    node_check(payload_text)
    report.append("payload: %d bytes of code, padded to %d, version=%r, live_url=%r" % (
        len(payload_text.encode("ascii")), PAYLOAD_BUDGET, args.version, args.live_url))

    with open(args.stock, "rb") as f:
        stock = f.read()
    patched = patch_module(stock, payload, report)
    print("patched module sha256:", sha256(patched))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "wb") as f:
        f.write(patched)
    payload_out = args.payload_out or os.path.join(os.path.dirname(args.out), "payload-built.js")
    os.makedirs(os.path.dirname(payload_out), exist_ok=True)
    with open(payload_out, "wb") as f:
        f.write(payload)
    print("wrote", args.out)
    print("wrote", payload_out)
    report.append("patched module sha256: %s" % sha256(patched))

    if not args.skip_outer:
        with open(args.stock_outer, "rb") as f:
            stock_outer = f.read()
        out_outer = repack_outer(stock_outer, stock, patched, report)
        with open(args.out_outer, "wb") as f:
            f.write(out_outer)
        print("wrote", args.out_outer)
        report.append("repacked outer sha256: %s" % sha256(out_outer))

    report.append("")
    report.append("Expected console log lines after deploy:")
    report.append("  [HOMEJS] RunScript in 'rnps-settings (NPXS40008) [...]'")
    report.append("  ANIKETOS installed for space ")
    report.append("  ANIKETOS webpack require captured, 2779 modules")
    report.append("  ANIKETOS version %s in module 945" % args.version)
    report.append("  ANIKETOS orig <real displayVersion> -> <fake swapped in>   (first System Information view)")
    if args.live_url:
        report.append("  ANIKETOS version <- <new value>   (after the PC sets one)")
    report.append("  ANIKETOS alive patched={...} errors=0 hooks=1")

    report_path = os.path.join(os.path.dirname(args.out), "build-report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    print("wrote", report_path)
    print("\n".join(report))
    print("== done ==")


if __name__ == "__main__":
    main()
