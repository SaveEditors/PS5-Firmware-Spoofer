# Troubleshooting

## Real version back after a shellui restart

Look for /user/data/AniketosHEN/js_inject_unconfirmed on the console. The
toolbox writes that marker when a shellui session went down while an
injection was in flight, and while it exists it skips every JS injection
("JavaScript left alone" in the log). Native things keep working, which is
why it looks like only the version mod is broken.

```
python tools/console_ftp.py del /user/data/AniketosHEN/js_inject_unconfirmed
```

then restart shellui once. Normal use doesn't re-arm it, only restarts during
an injection can.

## Live value doesn't arrive

- Server running? The page should open in a browser on the PC itself.
- /value hits from the console's IP in the server log? Expect two interleaved
  streams every ~2.5s.
- No hits: open the page on your phone. Phone fails too, it's the PC firewall
  (rule in [live-editing.md](live-editing.md)) or AP client isolation. Phone
  works but the console doesn't, then the build is missing --live-url or the
  console is on a different subnet.
- After a value change, reopen the System Information screen. And keep the
  value 5 characters.

## Nothing shows at all

Pull the log and look for ANIKETOS lines:

```
python tools/console_ftp.py tail /user/data/AniketosHEN/AniketosHEN_shellui.log 200
```

- "injected into 'rnps-settings ... ok=1" plus "version 99.99 in module 945"
  means the payload ran. Screen still looks stock? Reopen it, the view may be
  cached.
- No ANIKETOS lines after opening settings: either the injection was skipped
  (marker above) or the payload isn't running (start aniketos-modded again).
- "left alone" in the log: that's the marker. Delete it, restart shellui.
- Wrong build? Written for 12.60 on AniketosHEN 20261011, but other builds
  may work too. The builder warns when your files differ but carries on; it
  stops only when the expected code is missing at the offsets.
- js_inject_pending is normal, it's written while an injection runs and
  clears itself. Only js_inject_unconfirmed needs deleting.

## FAQ

**Does this affect PSN, updates or games?** No, they read the real version.
Only what Settings displays changes.

**Does it touch the kernel?** No, it's plain JS that wraps a getter, no
kernel r/w like the kernel-level fw spoof payloads.

**Do I have to redo anything after reboot?** Yes, run aniketos-modded again
like any payload.

**Can I use a different value?** Yes, anything from the page or baked with
--version. Live values up to 63 characters render fine, symbols included;
64 or more gets ignored. Five characters (like 99.99) is just what keeps the
row looking stock.

**How do I read console logs from the PC?** python tools/console_ftp.py tail
<path> [lines] or cat. The console's FTP plugin needs to be running
(port 1337).
