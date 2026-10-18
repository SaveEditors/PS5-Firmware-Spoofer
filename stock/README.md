# Stock files

The builder needs the exact AniketosHEN build the patch offsets were
written for. Copy these two files here:

| file | size | sha256 |
| --- | --- | --- |
| embedded_000d88c0.elf | 4,656,944 | 7b9212552a1f2bcb06bf89bdd83f3308007bd905e87e78d2acde27e0019487e9 |
| outer.elf | 28,436,984 | 38c3c50ddd4d989f8f168ff56f44113235b71d967ecc8415c10bedfdb076de68 |

Both are in the AniketosHEN 20261011 release. embedded_000d88c0.elf is the
shellui module, outer.elf is the stage2.

If your hashes differ, your build is different and these offsets do not
apply. The builder will refuse the file; please don't work around that.

The .elf files in this folder are gitignored.
