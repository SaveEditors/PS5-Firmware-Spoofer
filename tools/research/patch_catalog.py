"""
Same-size-string swap for Sce.PlayStation.PUI_UI3.rco locale catalogs.

PURPOSE
  Swap msgid catalog strings (Settings UI labels/header) in the en-US/default
  and en-GB plaintext JSON catalogs inside Sce.PlayStation.PUI_UI3.rco.

SAFETY MODEL
  - Output file is byte-identical in size to stock; only value bytes inside the
    two JSON blobs are changed (equal length), or value bytes + in-JSON padding
    (shorter new text: spaces are inserted between the ':' and the value quote,
    which is valid JSON whitespace).
  - No structural fields (tree, file table, data attribute offsets/sizes) change.

USAGE
  python patch_catalog.py                 -> writes out\Sce.PlayStation.PUI_UI3.rco
  Edit EDITS below to change target texts, rerun.

CONSTRAINT
  new text byte-length must be <= old text byte-length (same-size mode).
  If a longer text is needed, the whole blob must be rebuilt with corrected
  offsets (different pipeline, needs re-serialization; ask for 'redistribute').
"""
import json, hashlib, os, sys

RCO_IN   = r"B:\vsh_asset\Sce.PlayStation.PUI_UI3.rco"
OUT_DIR  = r"B:\ps5FWSPF\out"
AUD_DIR  = os.path.join(OUT_DIR, "audit")
RCO_OUT  = os.path.join(OUT_DIR, "Sce.PlayStation.PUI_UI3.rco")
MANIFEST = os.path.join(OUT_DIR, "patch-manifest.txt")

# (name -> (file_offset, size)) verified against RCO-NAMES.json + raw bytes
BLOBS = {
    "en-US/default": (18447808, 2168287),
    "en-GB":         (33882432, 2169945),
}

# DEMO BUILD (replace texts once final wording is confirmed)
EDITS = [
    {"locales": ["en-US/default", "en-GB"],
     "msgid": "msgid_system_information",
     "new":   "Console Info [Demo]"},          # stock: 'Console Information' (19)
    {"locales": ["en-US/default", "en-GB"],
     "msgid": "msgid_system_software_simple",
     "new":   "Firmware: v9.99"},              # stock: 'System software' (15)
]

def sha256(b):
    return hashlib.sha256(b).hexdigest()

def find_unique_value(blob, msgid):
    pat = b'"%s":"' % msgid.encode()
    i = blob.find(pat)
    if i < 0:
        raise SystemExit("msgid not found: " + msgid)
    if blob.find(pat, i + 1) >= 0:
        raise SystemExit("msgid not unique: " + msgid)
    gs = i + len(pat)
    ge = blob.find(b'"', gs)
    if ge < 0 or blob[ge - 1] == 0x5C:
        raise SystemExit("unexpected escaping for " + msgid)
    return i, gs, ge

def find_value_any(blob, msgid):
    """Locate value quotes even if padding spaces were inserted after ':'. """
    m = blob.find(b'"%s":' % msgid.encode())
    if m < 0:
        raise SystemExit("msgid not found (verify): " + msgid)
    q = blob.find(b'"', m + len(msgid) + 2)   # first quote after the colon
    z = blob.find(b'"', q + 1)
    return q, z

def main():
    stock = open(RCO_IN, 'rb').read()
    print("stock size      :", len(stock), "sha256", sha256(stock))
    data = bytearray(stock)

    # round-trip audit: can Python reproduce the blob byte-exactly?
    # (informational; used to decide 'redistribute' mode feasibility later)
    for name, (off, size) in BLOBS.items():
        blob = bytes(data[off:off + size])
        try:
            rt = json.dumps(json.loads(blob), ensure_ascii=False,
                            separators=(',', ':')).encode('utf-8')
            same = (rt == blob)
        except Exception as ex:
            same = "parse error: %s" % ex
        print("round-trip %-14s: %s" % (name, same))

    records = []
    for e in EDITS:
        new = e["new"].encode('utf-8')
        for locname in e["locales"]:
            off, size = BLOBS[locname]
            blob = bytes(data[off:off + size])
            i, gs, ge = find_unique_value(blob, e["msgid"])
            old = blob[gs:ge]
            if len(new) > len(old):
                raise SystemExit(
                    "LONGER text not supported in same-size mode: %s (%d->%d)"
                    % (e["msgid"], len(old), len(new)))
            if len(new) == len(old):
                abs_s, abs_e = off + gs, off + ge
                data[abs_s:abs_e] = new
                mode = "equal-length replace"
                rec_start = abs_s
                rec_old = old
                rec_new = new
            else:
                pad = len(old) - len(new)
                qs = gs - 1                      # opening quote of value
                abs_qs, abs_qe = off + qs, off + ge
                seg = b' ' * pad + b'"' + new + b'"'
                assert len(seg) == (ge - qs + 1)
                data[abs_qs:abs_qe + 1] = seg
                mode = "shorter + %d pad spaces before value" % pad
                rec_start = abs_qs
                rec_old = blob[qs:ge + 1]
                rec_new = seg
            records.append({
                "locale": locname, "msgid": e["msgid"], "mode": mode,
                "file_offset": rec_start,
                "old_hex": rec_old.hex(), "new_hex": rec_new.hex(),
                "old_text": rec_old.decode('utf-8', 'replace'),
                "new_text": rec_new.decode('utf-8', 'replace'),
            })
            print("patched %-14s %-32s %s" % (locname, e["msgid"], mode))

    # post-verification
    print("-" * 70)
    for name, (off, size) in BLOBS.items():
        blob = bytes(data[off:off + size])
        json.loads(blob)            # strict parse must succeed
        for e in EDITS:
            q, z = find_value_any(blob, e["msgid"])
            val = blob[q + 1:z]
            print("verify   %-14s %-32s -> %r" % (name, e["msgid"], val))
    same_size = len(data) == len(stock)
    print("size preserved  :", same_size, "(", len(data), ")")
    assert same_size

    # byte-diff summary
    diff = [k for k in range(len(stock)) if stock[k] != data[k]]
    ranges = []
    for k in diff:
        if ranges and k == ranges[-1][1] + 1:
            ranges[-1][1] = k
        else:
            ranges.append([k, k])
    print("changed ranges  :", [(a, b, b - a + 1) for a, b in ranges])

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(AUD_DIR, exist_ok=True)
    open(RCO_OUT, 'wb').write(bytes(data))
    print("written         :", RCO_OUT)
    print("size            :", len(data), "sha256", sha256(bytes(data)))

    for name, (off, size) in BLOBS.items():
        fn = os.path.join(AUD_DIR, name.replace('/', '_') + ".json")
        open(fn, 'wb').write(bytes(data[off:off + size]))
        print("audit blob      :", fn)

    with open(MANIFEST, 'w', encoding='utf-8') as f:
        f.write("Sce.PlayStation.PUI_UI3.rco string swap manifest\n")
        f.write("stock  sha256: %s\n" % sha256(stock))
        f.write("output sha256: %s\n" % sha256(bytes(data)))
        f.write("size: %d (unchanged)\n\n" % len(data))
        for r in records:
            f.write("locale %s\n" % r["locale"])
            f.write("  msgid : %s\n" % r["msgid"])
            f.write("  mode  : %s\n" % r["mode"])
            f.write("  offset: %d (0x%X)\n" % (r["file_offset"], r["file_offset"]))
            f.write("  old   : %r\n" % r["old_text"])
            f.write("  new   : %r\n" % r["new_text"])
            f.write("  old_hex: %s\n" % r["old_hex"])
            f.write("  new_hex: %s\n\n" % r["new_hex"])
    print("manifest        :", MANIFEST)

if __name__ == "__main__":
    main()
