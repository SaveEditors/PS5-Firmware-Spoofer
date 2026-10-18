import sys

path, off, length = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
d = open(path, "rb").read()[off:off + length]
for i in range(0, len(d), 16):
    chunk = d[i:i + 16]
    hexpart = " ".join(f"{b:02x}" for b in chunk)
    txt = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
    print(f"{off + i:08x}  {hexpart:<48}  {txt}")
