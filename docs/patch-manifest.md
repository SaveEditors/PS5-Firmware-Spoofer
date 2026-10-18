PATCH MANIFEST - PS5 FW 12.60 (AniketosHEN build 20261011)
==========================================================

(Historical build record; stock inputs live in stock/, outputs in out/.)

==============================================================================
PART 1: shellui patch (fake version + live value)
==============================================================================

files
  stock : embedded_000d88c0.elf
          size 4656944
          sha256 7b9212552a1f2bcb06bf89bdd83f3308007bd905e87e78d2acde27e0019487e9
  stock : outer.elf
          size 28436984
          sha256 38c3c50ddd4d989f8f168ff56f44113235b71d967ecc8415c10bedfdb076de68

  output A (live build; primary):
    out\embedded_000d88c0.modded.elf
          size 4656944 (unchanged)
          sha256 630b0b6b4530a9eb50a541996cb9df79556ff61bc6b4e83b729d5256dd7d4835
    out\stage2.modded.elf
          size 28436984 (unchanged; module spliced at 0xD88C0)
          sha256 fa948bbde2bfef3da25550882162f8f93b555efe18be77a486fb70fa5f993320
          deployed on console: /data/pldmgr/payloads/local/aniketos-modded/stage2.modded.elf
          (sha256 checked after upload)

  output B (offline build; no network):
    out\embedded_000d88c0.modded-offline.elf
          size 4656944 (unchanged)
          sha256 a69c678200b83bbe3cf082896f92592db5e9d910e886eb80037c350ee6da08ff
    out\stage2.modded-offline.elf
          size 28436984 (unchanged; module spliced at 0xD88C0)
          sha256 ce490208b383246cfffce80f966a87703f6992657960d9703670eedcff0e3e8c

byte patches (module file, all same-size; identical in both builds)
  0x0E68BC  old 72                    new 73
            loop2 memchr char 'r' -> 's' (new needle starts with 's')
  0x0E6921  old 410f95c4              new 41b40190
            mov r12b,1; nop  (force bVar22 = true; was setne r12b)
  0x28F6A0  old 'rnps-control-cen'    new 'settings (NPXS40'
            old_hex 726e70732d636f6e74726f6c2d63656e
            new_hex 73657474696e677320284e5058533430
  0x28F590  old 's-control-center'    new 'tings (NPXS40008'
            old_hex 732d636f6e74726f6c2d63656e746572
            new_hex 74696e677320284e5058533430303038

payload
  file offset   0x296B20 (string slot; NUL at 0x298A32, data table at 0x298A34)
  budget        7954 bytes (exact stock slot size)
  version       99.99 (baked in both builds; swaps the '12.60' token inside the
                real displayVersion string -> same length/format; change with
                apply_mod.py --version)
  A live built  7833 bytes of code + spaces to 7954
  A live url    http://<PC-IP>:8909/value
  A live sha256 cd1fbd2ef77bcb20a7e70fd0dc4e19f0266e8ade7fac23e044023dd7738eb9fc
  B off. built  7802 bytes of code + spaces to 7954
  B off. url    (none)
  B off. sha256 3aa0c671f1d9f57d17026a494a4511b96cec1c1850affb13354df5f879a2eac5
  payload adds  early 'ANIKETOS alive' beacon at 1.5 s (watchdog line before
                the install work), cfg defaults to
                {} when the native config global is absent, module-cache scan
                (require.c) patches modules that ran before the trap armed,
                displayVersion token swap + one-shot 'ANIKETOS orig <real> ->
                <fake>' log line (first System Information view)
  source        tools\payload_template.js
  exact bytes   out\payload-built-live.js
                out\payload-built-offline.js
  stock payload out\homejs-payload.js (reference, 7954 bytes)

rebuild
  live   : python tools\apply_mod.py --version 99.99 --live-url http://<PC-IP>:8909/value
  offline: python tools\apply_mod.py --version 99.99 --out out\embedded_000d88c0.modded-offline.elf --out-outer out\stage2.modded-offline.elf --payload-out out\payload-built-offline.js

console blocker (cleared 2026-10-16)
  /user/data/AniketosHEN/js_inject_unconfirmed (0 B, Oct 14) made the toolbox
  skip all JS injection ("the last injection did not finish; JavaScript left
  alone"). It was deleted with tools\console_ftp.py (new 'del' command). The
  toolbox recreates markers by itself if an injection cannot be confirmed.

live editing
  PC   : python tools\fake_version_server.py   (http://<PC-IP>:8909/)
  flow : browser Set -> settings app polls /value every 2.5 s -> visible on next
         visit to Settings > System > System Information
  watch: the server log shows every console hit (the 2.5 s /value polls).
         The payload's own console.log lines are echoed into
         AniketosHEN_shellui.log as '[HOMEJS] js: ...' lines; an applied
         live value appears as 'ANIKETOS version <- <value>'.
  scope: display-only spoof; real firmware/update path untouched
         (prefixVersion stays real; the live value replaces only the '12.60'
         token inside the full string - use 5 characters to keep its length)

==============================================================================
PART 2: RCO overlay strings (Settings > System > System Information)
         [optional; decision was to keep stock labels, demo file kept as proof]
==============================================================================

  stock : Sce.PlayStation.PUI_UI3.rco
          size 105673600
          sha256 e7324ad17f37000d205d98d99910f418cf2dbc5be18c93363dc7cdc39639e99f
  output: out\Sce.PlayStation.PUI_UI3.rco   [DEMO texts only]
          size 105673600 (unchanged)
          sha256 65f54736980ab5ca9f4f7d43322a5e52f7559dccb74ec682e5242b5b17dd949a

locale en-US/default
  msgid : msgid_system_information
  mode  : equal-length replace
  offset: 20275611 (0x135619B)
  old   : 'Console Information'
  new   : 'Console Info [Demo]'
  old_hex: 436f6e736f6c6520496e666f726d6174696f6e
  new_hex: 436f6e736f6c6520496e666f205b44656d6f5d

locale en-GB
  msgid : msgid_system_information
  mode  : equal-length replace
  offset: 35711602 (0x220EA72)
  old   : 'Console Information'
  new   : 'Console Info [Demo]'
  old_hex: 436f6e736f6c6520496e666f726d6174696f6e
  new_hex: 436f6e736f6c6520496e666f205b44656d6f5d

locale en-US/default
  msgid : msgid_system_software_simple
  mode  : equal-length replace
  offset: 20278383 (0x1356C6F)
  old   : 'System software'
  new   : 'Firmware: v9.99'
  old_hex: 53797374656d20736f667477617265
  new_hex: 4669726d776172653a2076392e3939

locale en-GB
  msgid : msgid_system_software_simple
  mode  : equal-length replace
  offset: 35714372 (0x220F544)
  old   : 'System software'
  new   : 'Firmware: v9.99'
  old_hex: 53797374656d20736f667477617265
  new_hex: 4669726d776172653a2076392e3939

  status: optional. Part 1 alone fakes the version value; label rewording is
          available if you want it (say which row + new text).
  regenerate: edit EDITS in tools\research\patch_catalog.py and rerun
