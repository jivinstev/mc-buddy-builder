#!/usr/bin/env python3
"""Fail if the cloud domain list in docs/CLOUD.md differs from cloud/allowed-domains.txt."""
import pathlib, sys
root = pathlib.Path(__file__).resolve().parent.parent
lines = {l.strip() for l in root.joinpath('docs/CLOUD.md').read_text().splitlines()}
domains = [l.strip() for l in root.joinpath('cloud/allowed-domains.txt').read_text().splitlines() if l.strip()]
missing = [d for d in domains if d not in lines]
print('check_readme: %d domains, %s' % (len(domains), 'in sync' if not missing else 'DRIFTED'))
for m in missing:
    print('  docs/CLOUD.md is missing  ' + m)
sys.exit(1 if missing else 0)
