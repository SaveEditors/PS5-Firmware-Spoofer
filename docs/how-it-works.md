# How it works

What the patches actually do. You don't need any of this to use the mod.

## The shellui injection

The shellui module has a native dispatcher that matches each app context
against needle strings and injects a JS payload when one matches. Stock, only
the home context matches ("rnps-home"); a second branch looking for
"rnps-control-center" is dead on retail because its gate flag reads 0.

Four same-size edits repoint that dead branch at the settings context and
force the gate open:

| offset | change |
| --- | --- |
| 0x0E68BC | r -> s (memchr char; the new needle starts with s) |
| 0x0E6921 | setne r12b -> mov r12b,1; nop (gate always true) |
| 0x28F6A0 | "rnps-control-cen" -> "settings (NPXS40" |
| 0x28F590 | "s-control-center" -> "tings (NPXS40008" |

Settings contexts are named like "rnps-settings (NPXS40008) [uuid]", both
needle halves match, injection runs. The module file never changes length.

## The payload

The payload is the stock AniketosHEN script plus a version wrapper. It grabs
webpack's private require (both call shapes, home with 4 args, settings with
5), also scans the module cache for late modules, and reaches module 945, the
settings app's Info namespace, where it wraps getSystemSoftwareVersion and
getSystemSoftwareVersionSync.

The wrapper copies the returned object and swaps the "12.60" token inside
displayVersion for the fake value. Everything else, prefixVersion included,
is left alone. If the token is missing it falls back to the bare fake value.
Nothing is sanitized or length-checked, the row renders whatever is set; the
5-character default is only what keeps the string exactly stock-length.

The first swap logs once: ANIKETOS orig <real> -> <fake>.

## Live poll

Each patched context starts a 2.5s XMLHttpRequest poll of .../value?x=<time>
when it was built with --live-url. When the value differs it becomes the new
fake and logs ANIKETOS version <- <value>. Values 64 characters or longer
are ignored and the current one keeps showing. The wrapper reads the value
at call time, so the new number shows up the next time the screen is opened.
If the server is down the poll fails quietly and the baked value stays. The
offline build has no URL and never polls.

## Watchdog lines

ANIKETOS alive early (~1.5s, before the install work) and ANIKETOS alive
patched={...} errors=0 (~8s) are what the native side treats as an injection
that finished. A session that dies before these lines is what triggers the
js_inject_unconfirmed marker described in troubleshooting.

## Why not a kernel patch

Kernel-level version spoofs change what the whole system reports. This one
only changes what the Settings app draws. Updates and system logic keep
seeing the real version, nothing writes to the kernel. That is intentional.
If you need the system-wide value spoofed, that is another tool.
