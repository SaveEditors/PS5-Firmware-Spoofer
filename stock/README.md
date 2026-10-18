# Stock files

Copy the AniketosHEN 12.60 files here, one per row:

| file | size | sha256 |
| --- | --- | --- |
| embedded_000d88c0.elf | 4,656,944 | 7b9212552a1f2bcb06bf89bdd83f3308007bd905e87e78d2acde27e0019487e9 |
| outer.elf | 28,436,984 | 38c3c50ddd4d989f8f168ff56f44113235b71d967ecc8415c10bedfdb076de68 |

Both are in the AniketosHEN 20261011 release, the build everything here was
written against. embedded_000d88c0.elf is the shellui module, outer.elf is
the stage2.

The hashes are not enforced: other builds may work just as well (etaHEN or
onionHEN setups included). When your files don't match, the builder warns and
carries on. It still checks the byte offsets themselves: if the expected code
is not there, it stops with an error instead of writing something broken.

The .elf files in this folder are gitignored.
