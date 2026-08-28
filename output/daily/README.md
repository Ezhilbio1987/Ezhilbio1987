# Daily editions

The 6 am job writes each morning's paper here as `<YYYY-MM-DD>.pdf` and pushes
it, so every edition has a stable link:

```
https://github.com/Ezhilbio1987/Ezhilbio1987/raw/claude/tamil-newspaper-creation-8toaev/output/daily/2026-08-29.pdf
```

Editions are kept for 30 days. Older ones are removed by the daily job — a
paper a day at a couple of megabytes would otherwise grow the repository by
about a gigabyte a year. Nothing is lost that cannot be rebuilt: the edition
file that produced each PDF is committed alongside it.
