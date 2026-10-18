"""Deploy the modded stage2 ELF to the console payload manager (PLDMGR).

Creates /data/pldmgr/payloads/local/<name>/ on the console (over the
AniketosHEN FTP plugin) with the ELF + meta.json, then verifies the upload
by re-downloading it and comparing sha256.

Usage:
  python tools/deploy_pldmgr.py --host 192.168.1.155
  python tools/deploy_pldmgr.py --host 192.168.1.155 --elf out/stage2.modded.elf

Requires the console's FTP plugin to be running (default port 1337).
"""
import argparse
import datetime
import ftplib
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

DEFAULT_ELF = os.path.join(REPO, "out", "stage2.modded.elf")
REMOTE_NAME = "stage2.modded.elf"


def connect(host, port):
    ftp = ftplib.FTP()
    ftp.connect(host, port, timeout=30)
    ftp.login()
    ftp.set_pasv(True)
    return ftp


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="192.168.1.155", help="console IP (FTP plugin)")
    ap.add_argument("--port", type=int, default=1337, help="FTP plugin port")
    ap.add_argument("--elf", default=DEFAULT_ELF, help="local stage2 ELF to upload")
    ap.add_argument("--name", default="aniketos-modded", help="payload folder name on the console")
    args = ap.parse_args()

    remote_dir = "/data/pldmgr/payloads/local/" + args.name

    with open(args.elf, "rb") as f:
        local = f.read()
    local_sha = hashlib.sha256(local).hexdigest()

    meta = {
        "schema": 2,
        "kind": "local",
        "filename": REMOTE_NAME,
        "installed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "origin": "ftp_upload",
        "origin_detail": ("ps5FWSPF build - Settings shows the stock version string "
                          "with its firmware number swapped (same length/format); "
                          "display-only"),
    }
    meta_bytes = (json.dumps(meta, indent=2) + "\n").encode("utf-8")

    ftp = connect(args.host, args.port)
    try:
        try:
            ftp.mkd(remote_dir)
            print("mkdir", remote_dir)
        except ftplib.error_perm as e:
            print("mkdir skipped (exists?):", e)

        with open(args.elf, "rb") as f:
            ftp.storbinary("STOR %s/%s" % (remote_dir, REMOTE_NAME), f,
                           blocksize=1 << 20)
        print("uploaded", REMOTE_NAME, len(local), "bytes")

        ftp.storbinary("STOR %s/meta.json" % remote_dir, io.BytesIO(meta_bytes))
        print("uploaded meta.json")

        print("remote SIZE:", ftp.size("%s/%s" % (remote_dir, REMOTE_NAME)))
        buf = io.BytesIO()
        ftp.retrbinary("RETR %s/%s" % (remote_dir, REMOTE_NAME), buf.write,
                       blocksize=1 << 20)
        remote_sha = hashlib.sha256(buf.getvalue()).hexdigest()
        print("local  sha256:", local_sha)
        print("remote sha256:", remote_sha)
        ok = remote_sha == local_sha
        print("MATCH:", ok)

        lines = []
        ftp.retrlines("LIST " + remote_dir, lines.append)
        print("\n".join(lines))
        if not ok:
            sys.exit(1)
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()


if __name__ == "__main__":
    main()
