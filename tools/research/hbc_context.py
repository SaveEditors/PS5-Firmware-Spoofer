import re

HBC = r"B:\NPXS40008_dec\NPXS40008.hbc"
d = open(HBC, 'rb').read()

def ctx(needle, span=90, max_hits=6):
    print('#' * 78)
    print('NEEDLE', needle)
    n = 0
    start = 0
    while True:
        i = d.find(needle, start)
        if i < 0 or n >= max_hits:
            break
        a = max(0, i - span)
        b = min(len(d), i + len(needle) + span)
        chunk = d[a:b]
        txt = ''.join(chr(c) if 32 <= c < 127 else '.' for c in chunk)
        print('@0x%08x ctx: %s' % (i, txt))
        # also hex of a tighter window around the needle
        a2 = max(0, i - 16); b2 = min(len(d), i + len(needle) + 32)
        print('   hex: %s' % d[a2:b2].hex())
        n += 1
        start = i + 1
    if n == 0:
        print('  (none)')

ctx(b'pssettings')
ctx(b'debug_settings')
ctx(b'id_system_software')
ctx(b'displayVersion')
ctx(b'SystemInfoTurboModule')
ctx(b'GetSystemSoftwareVersion')
