# Live value

A build made with --live-url polls the given URL every 2.5 seconds and sets
the version number to whatever the server answers. The row updates within a
few seconds, but you usually have to reopen the System Information screen to
see it.

## Server

```
python tools/fake_version_server.py
```

Prints the address to open, something like http://192.168.1.50:8909/, and
stores the current value in tools/live_version.txt so it survives restarts.

## Windows firewall

Without a firewall rule the console's requests get dropped silently and the
server log stays empty. This looks like the mod is broken, it is not.
One-time fix, admin PowerShell:

```powershell
New-NetFirewallRule -DisplayName "Aniketos live version 8909" -Direction Inbound -Protocol TCP -LocalPort 8909 -Action Allow -Profile Private
```

## Using it

Open the page from any browser on the same network, phone included, type a
value and hit Set. The row renders whatever you send, symbols included, as
long as it is under 64 characters. Five characters (like 99.99) is just what
keeps the version string the same length as stock:
26.01-12.60.00.06-... becomes 26.01-99.99.00.06-....

Plain http on your LAN, no TLS. The live value is temporary; it lasts as
long as the payload keeps polling. To change the baked default, rebuild with
--version.

## Checking it works

Server side, a hit every ~2.5s from the console's IP. Two interleaved streams
are normal, the home and settings contexts each poll:

```
192.168.1.155 - "GET /value?x=1792269929024 HTTP/1.1" 200 -
```

Console side, one line each time a new value is picked up:

```
[HOMEJS] js: ANIKETOS version <- 88.88
```

If neither shows up: firewall rule missing, console and PC on different
networks, or the build has no live URL at all (the offline build never
polls).
