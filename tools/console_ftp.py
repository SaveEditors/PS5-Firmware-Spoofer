"""Tiny FTP helper for the PS5 console (192.168.1.155:1337).

usage:
  python tools/console_ftp.py ls [path]
  python tools/console_ftp.py put <local-file> <remote-path>
"""
import argparse
import ftplib
import os
import sys

DEFAULT_HOST = "192.168.1.155"
DEFAULT_PORT = 1337


def connect(host, port):
    ftp = ftplib.FTP()
    ftp.connect(host, port, timeout=20)
    try:
        ftp.login()
    except ftplib.error_perm:
        ftp.login("anonymous", "")
    ftp.set_pasv(True)
    return ftp


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ls")
    p.add_argument("path", nargs="?", default="/")

    p = sub.add_parser("put")
    p.add_argument("local")
    p.add_argument("remote")

    p = sub.add_parser("cat")
    p.add_argument("path")

    p = sub.add_parser("tail")
    p.add_argument("path")
    p.add_argument("n", type=int, nargs="?", default=100)

    p = sub.add_parser("del")
    p.add_argument("path")

    args = ap.parse_args()
    ftp = connect(args.host, args.port)
    print("connected:", ftp.getwelcome())
    try:
        if args.cmd == "ls":
            lines = []
            ftp.retrlines("LIST " + args.path, lines.append)
            for ln in lines:
                print(ln)
        elif args.cmd == "put":
            size = os.path.getsize(args.local)
            with open(args.local, "rb") as fp:
                ftp.storbinary("STOR " + args.remote, fp, blocksize=1 << 20)
            print("uploaded %s (%d bytes) -> %s" % (args.local, size, args.remote))
        elif args.cmd == "cat":
            import io
            buf = io.BytesIO()
            ftp.retrbinary("RETR " + args.path, buf.write)
            data = buf.getvalue()
            print(data.decode("utf-8", errors="replace"))
        elif args.cmd == "tail":
            import io
            buf = io.BytesIO()
            ftp.retrbinary("RETR " + args.path, buf.write)
            data = buf.getvalue().decode("utf-8", errors="replace")
            for ln in data.splitlines()[-args.n:]:
                print(ln)
        elif args.cmd == "del":
            ftp.delete(args.path)
            print("deleted", args.path)
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()


if __name__ == "__main__":
    main()
