import json, sys

RCO = r"B:\vsh_asset\Sce.PlayStation.PUI_UI3.rco"
data = open(RCO, 'rb').read()
print("RCO size:", len(data))

blobs = {
    'en-US/default': (18447808, 2168287),
    'en-GB':         (33882432, 2169945),
}

keys = ["msgid_system_information","msgid_system_software_simple","msgid_system_software",
        "msgid_system_software_version_num","msgid_serial_number","msgid_mac_address_lan",
        "msgid_mac_address_wifi","msgid_ipv4_address_simple","msgid_ipv6_address_simple",
        "msgid_ip_address_dev","msgid_system_language","msgid_system_storage_label"]

def find_value(blob, key):
    pat = b'"%s":"' % key.encode()
    res = []
    i = 0
    while True:
        i = blob.find(pat, i)
        if i < 0:
            break
        vstart = i + len(pat)
        j = vstart
        while True:
            j = blob.find(b'"', j)
            if j < 0:
                raise RuntimeError("unterminated value for " + key)
            k = j - 1
            nb = 0
            while k >= vstart and blob[k] == 0x5C:
                nb += 1
                k -= 1
            if nb % 2 == 0:
                break
            j += 1
        res.append((i, vstart, j, blob[vstart:j]))
        i = j + 1
    return res

for name, (off, sz) in blobs.items():
    blob = data[off:off+sz]
    print('=' * 78)
    print(name, '| file span', off, '->', off + sz, '| size', sz)
    print(' first 90:', blob[:90])
    print(' last 90 :', blob[-90:])
    try:
        json.loads(blob)
        print(' json.loads(whole blob): OK')
    except Exception as e:
        print(' json.loads(whole blob) FAILED:', str(e)[:120])
    for k in keys:
        hits = find_value(blob, k)
        if not hits:
            print('  %-34s NOT FOUND' % k)
            continue
        for (i, vstart, j, val) in hits:
            print('  %-34s @blob+%-8d file %-9d len %-3d %r' % (k, i, off + i, j - vstart, val))

# gap bytes between en-US end and ar-AE start
print('=' * 78)
print('gap bytes [20616095..20616097):', data[20616095:20616097])
print('gap bytes around en-GB end 36052377..36052384:', data[36052377:36052384])
