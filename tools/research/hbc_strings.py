import re

HBC = r"B:\NPXS40008_dec\NPXS40008.hbc"
d = open(HBC, 'rb').read()
print('hbc size', len(d), 'magic', d[:8].hex())

pattern = re.compile(rb'[\x20-\x7e]{5,}')
tokens = [b'pssettings', b'debug_settings', b'id_system_software', b'system_software',
          b'Aniketos', b'ANIKETOS', b'label', b'footer', b'displayVersion',
          b'SystemInfoTurboModule', b'GetSystemSoftwareVersion', b'pssettings:play',
          b'System software', b'Console Information', b'12.60', b'spoof']

hits = {t: [] for t in tokens}
count = 0
for m in pattern.finditer(d):
    count += 1
    s = m.group()
    for t in tokens:
        if t in s and len(hits[t]) < 12:
            hits[t].append((m.start(), s[:120]))

print('total ascii runs >=5:', count)
for t, lst in hits.items():
    print('=' * 70)
    print('TOKEN', t, 'hits:', len(lst))
    for off, s in lst:
        print('  @0x%08x %r' % (off, s))
