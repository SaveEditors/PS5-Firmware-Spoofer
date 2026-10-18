# Install

These steps assume AniketosHEN (build 20261011) is set up on a 12.60 console
and that you know how to run a stage2 payload from its payload manager.

## What the patch changes

Stock, the shellui module injects its JS payload into the home app only. Four
same-size byte edits point the second injection branch (control-center, dead
on retail) at the Settings app, and the module's embedded payload is replaced
with one that swaps the version number:

| offset | stock | patched | what |
| --- | --- | --- | --- |
| 0x0E68BC | 72 | 73 | memchr char, new needle starts with 's' |
| 0x0E6921 | 41 0F 95 C4 | 41 B4 01 90 | settings gate forced true |
| 0x28F6A0 | "rnps-control-cen" | "settings (NPXS40" | needle, first half |
| 0x28F590 | "s-control-center" | "tings (NPXS40008" | needle, second half |

Home injection stays on the stock path. The payload slot keeps its stock
7954 bytes (NUL at 0x298A32).

## Build

Get the stock files into stock/ first, see
[stock/README.md](../stock/README.md).

```
# live build: value changeable from a browser
python tools/apply_mod.py --version 99.99 --live-url http://<PC-IP>:8909/value \
    --payload-out out/payload-built-live.js

# offline build
python tools/apply_mod.py --version 99.99 \
    --out out/embedded_000d88c0.modded-offline.elf \
    --out-outer out/stage2.modded-offline.elf \
    --payload-out out/payload-built-offline.js
```

Outputs:

- out/embedded_000d88c0.modded.elf (4,656,944 bytes)
- out/stage2.modded.elf (28,436,984 bytes, module spliced in at 0xD88C0)
- out/payload-built-*.js, the exact payload bytes
- out/build-report.txt

## Install on the console

```
python tools/deploy_pldmgr.py --host <console-ip>
```

Uploads to /data/pldmgr/payloads/local/aniketos-modded/ and re-downloads the
file to compare sha256. Any FTP client works too, just drop the elf and a
meta.json in that folder.

Run aniketos-modded from the payload manager, open
Settings > System > System Information. Expected row:

```
26.01-99.99.00.06-00.00.00.0.1
```

The shellui log at /user/data/AniketosHEN/AniketosHEN_shellui.log should
show (among other lines):

```
[HOMEJS] RunScript in 'rnps-settings (NPXS40008) [<uuid>]'
ANIKETOS version 99.99 in module 945
ANIKETOS orig 26.01-12.60.00.06-00.00.00.0.1 -> 26.01-99.99.00.06-00.00.00.0.1
ANIKETOS alive patched={...} errors=0
```

The orig line is logged once, and it is the console's real version string.
Read the log from a PC with:

```
python tools/console_ftp.py tail /user/data/AniketosHEN/AniketosHEN_shellui.log 200
```

console_ftp.py connects to 192.168.1.155 by default, add --host <console-ip>
if that is not your console.

## js_inject_unconfirmed

If the version shows up real again after a shellui restart, look for
/user/data/AniketosHEN/js_inject_unconfirmed on the console. The toolbox
writes that marker when a shellui session died while an injection was still
in flight, and while it exists every JS injection is skipped. Delete it,
restart shellui once:

```
python tools/console_ftp.py del /user/data/AniketosHEN/js_inject_unconfirmed
```

Background in [troubleshooting.md](troubleshooting.md).

## Rollback

Run your normal AniketosHEN payload again, or reboot. The patch only exists
inside the payload that is running, nothing persistent. Delete
/data/pldmgr/payloads/local/aniketos-modded/ to clean up the upload.
