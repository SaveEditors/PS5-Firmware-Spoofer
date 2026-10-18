# PS5 Firmware spoofer (Live editing + Offline)

Changes the system software version shown in Settings > System > System
Information on firmware 12.60, built on top of AniketosHEN.

Only the firmware number inside the string is swapped, so the row keeps its
normal shape and length:

```
real    26.01-12.60.00.06-00.00.00.0.1
shown   26.01-99.99.00.06-00.00.00.0.1
```

Nothing else is affected. The version the system actually reports stays real
(updates, PSN and games keep seeing it), no kernel code is touched, and the
AniketosHEN home screen features work exactly as before. The value can also
be changed live from a browser while the console is running.

Video: https://x.com/SaveEditors/status/2111567506909565087

## What you need

- PS5 on 12.60 (not tested on other firmware versions)
- AniketosHEN build 20261011 (other builds have not been tested; may work on
  etaHEN/onionHEN too. The builder warns when your files differ instead of
  stopping, see [stock/README.md](stock/README.md))
- a way to run a stage2 payload, i.e. the payload manager in AniketosHEN
- Python 3 for building. Node is optional, it only adds a payload syntax
  check.

## Build

Put the two stock files in stock/, then:

```
# live build: value changeable from a browser
python tools/apply_mod.py --version 99.99 --live-url http://<PC-IP>:8909/value \
    --payload-out out/payload-built-live.js

# offline build: never touches the network
python tools/apply_mod.py --version 99.99 \
    --out out/embedded_000d88c0.modded-offline.elf \
    --out-outer out/stage2.modded-offline.elf \
    --payload-out out/payload-built-offline.js
```

Output lands in out/. There is also a prebuilt stage2.modded.elf on the
releases page.

## Install

```
python tools/deploy_pldmgr.py --host <console-ip>
```

Uploads out/stage2.modded.elf to
/data/pldmgr/payloads/local/aniketos-modded/ and compares the sha256 after
the upload. Then run aniketos-modded from the payload manager and open
System Information. The row should read:

```
26.01-99.99.00.06-00.00.00.0.1
```

## Live value

```
python tools/fake_version_server.py
```

Open the printed address from any device on the same network and set a new
value. One catch: Windows needs a firewall rule or the console cannot reach
the server. Details in [docs/live-editing.md](docs/live-editing.md).

## Known issues

- The real version can come back after restarting SceShellUI. The toolbox
  then has a js_inject_unconfirmed marker sitting around and skips all JS
  injection until it is deleted. Fix in
  [docs/troubleshooting.md](docs/troubleshooting.md).
- Live value not showing up is almost always the firewall
  ([docs/live-editing.md](docs/live-editing.md)).

## Docs

- [docs/install.md](docs/install.md) - build, deploy, expected console logs,
  rollback
- [docs/live-editing.md](docs/live-editing.md) - the PC/phone value server
  and firewall
- [docs/how-it-works.md](docs/how-it-works.md) - the four byte patches,
  payload internals
- [docs/troubleshooting.md](docs/troubleshooting.md) - marker, network, FAQ
- [docs/patch-manifest.md](docs/patch-manifest.md) - hashes and offsets of
  the current build
- [docs/rco-overlay.md](docs/rco-overlay.md) - optional, editing the static
  labels on that screen

## Repo layout

```
stock/   your AniketosHEN files (gitignored)
tools/   build and deploy scripts (+ tools/research, old decomp helpers)
docs/    documentation
out/     build output (gitignored)
```

## Rollback

Load your normal AniketosHEN payload again, or reboot. Nothing persistent is
modified: the patch only exists in the payload that is running. You can also
delete /data/pldmgr/payloads/local/aniketos-modded/ to clean up.

## Credits

Shellui injection concept and the base payload come from AniketosHEN, thanks
to its authors.

## License

MIT, see LICENSE.
