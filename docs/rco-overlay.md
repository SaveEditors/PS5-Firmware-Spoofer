# Optional: label edits (RCO)

Not part of the version spoof and not needed for it. The version value is
runtime data and handled by the payload; this is only about the static labels
around it, which live in the UI catalog Sce.PlayStation.PUI_UI3.rco.

Recommendation: leave the labels stock. A spoofed console should still look
normal. But the same-size edit does work, so here is the reference in case
you want it.

| item | value |
| --- | --- |
| console path | /system_ex/vsh_asset/Sce.PlayStation.PUI_UI3.rco |
| size | 105,673,600 bytes (same as stock) |
| demo build sha256 | 65f54736980ab5ca9f4f7d43322a5e52f7559dccb74ec682e5242b5b17dd949a |
| stock sha256 | e7324ad17f37000d205d98d99910f418cf2dbc5be18c93363dc7cdc39639e99f |

The demo file in out/ (local build, not committed) changes two strings in
the en-US/default and en-GB catalogs:

- msgid_system_information: "Console Information" -> "Console Info [Demo]"
- msgid_system_software_simple: "System software" -> "Firmware: v9.99"

Only value bytes inside the two plaintext JSON catalogs change; all structure
stays where it was. Seven strings on that page can be swapped this way
(header, system software, IPv4, IPv6, MAC for LAN and Wi-Fi, serial number).

## Applying it

1. Put the file in a replacement directory mirroring /system_ex/vsh_asset.
   nullfs covers the whole directory, so the original sibling files have to
   be in there too.
2. Cover the consuming process's sandbox view, e.g.
   /mnt/sandbox/NPXS40087_NNN/system_ex/vsh_asset. If settings resolves
   through its own sandbox, cover that one as well.
3. Strings not refreshing? Reopen the screen first. Then restart shellui and
   cover the new sandbox suffix.

Revert by unmounting, or keep the stock file around as the fallback copy.

## Regenerating

tools/research/patch_catalog.py, input/output paths are hardcoded at the top.
Same-size mode (the default) needs the new text to fit in the old text's
bytes; shorter texts get space padding inside the JSON. Longer texts are
possible as long as the whole catalog still fits the original blob size.
