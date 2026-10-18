import sys

path = sys.argv[1]
d = open(path, "rb").read()
print(f"== {path} ({len(d)} bytes)")
for arg in sys.argv[2:]:
    n = arg.encode("latin-1")
    hits = []
    i = 0
    while True:
        i = d.find(n, i)
        if i < 0:
            break
        hits.append(i)
        i += 1
    print(f"   {arg!r}: {len(hits)} hits {[hex(h) for h in hits[:8]]}")
