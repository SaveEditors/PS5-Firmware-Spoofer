import struct

p = r"A:\Developer\Build-validation\AniketosHEN-20261011\modules\embedded_000d88c0.elf"
d = open(p, 'rb').read()
print('size', len(d))
assert d[:4] == b'\x7fELF'

e_phoff = struct.unpack_from('<Q', d, 0x20)[0]
e_phentsize = struct.unpack_from('<H', d, 0x36)[0]
e_phnum = struct.unpack_from('<H', d, 0x38)[0]
segs = []
for i in range(e_phnum):
    o = e_phoff + i * e_phentsize
    (p_type,) = struct.unpack_from('<I', d, o)
    p_offset, p_vaddr, p_paddr, p_filesz, p_memsz = struct.unpack_from('<QQQQQ', d, o + 8)
    if p_type == 1:
        segs.append((p_offset, p_vaddr, p_filesz))
        print(f"LOAD off=0x{p_offset:x} vaddr=0x{p_vaddr:x} filesz=0x{p_filesz:x} memsz=0x{p_memsz:x}")

def va2off(va):
    for off, vaddr, filesz in segs:
        if vaddr <= va < vaddr + filesz:
            return off + (va - vaddr)
    return None

for va, n in [(0x38b0c0, 48), (0x38aff0, 48), (0x38b470, 48), (0x38b610, 32), (0x3906d0, 96)]:
    o = va2off(va)
    print(f"--- VA 0x{va:x} -> file off {('0x%x' % o) if o is not None else None}")
    if o is not None:
        b = d[o:o + n]
        print('  hex  :', b.hex())
        print('  ascii:', ''.join(chr(c) if 32 <= c < 127 else '.' for c in b))
