#!/usr/bin/env python3
"""Generate or verify the CES source-package SHA-256 manifest."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / '.claude/engineering-system/package-integrity.json'
EXCLUDED_PARTS = {'runtime', 'backups', '__pycache__', '.git'}
EXCLUDED_FILES = {'.claude/engineering-system/installed-files.json', '.claude/engineering-system/package-integrity.json', '.claude/settings.json', '.claude/settings.local.json'}

def version() -> str:
    text=(ROOT/'scripts/claude/lib/common.php').read_text()
    m=re.search(r"const VERSION = '([^']+)';", text)
    if not m:
        raise SystemExit('Could not read CES version')
    return m.group(1)

def files() -> dict[str,str]:
    out={}
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or p.is_symlink():
            continue
        rel=p.relative_to(ROOT).as_posix()
        if rel in EXCLUDED_FILES or any(part in EXCLUDED_PARTS for part in p.relative_to(ROOT).parts):
            continue
        if p.suffix in {'.pyc','.zip'}:
            continue
        out[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
    return out

def expected() -> str:
    obj={'version':version(),'algorithm':'sha256','scope':'source repository/package excluding this manifest, runtime/backups/installer state, VCS metadata, caches and ZIP outputs','files':files()}
    return json.dumps(obj,indent=2,ensure_ascii=False)+"\n"

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--check',action='store_true'); args=ap.parse_args()
    data=expected()
    if args.check:
        if not MANIFEST.exists() or MANIFEST.read_text()!=data:
            print('package-integrity.json is stale; run: python3 tools/package_integrity.py')
            return 2
        print(f'package integrity manifest OK ({len(files())} files, version {version()})')
        return 0
    MANIFEST.parent.mkdir(parents=True,exist_ok=True); MANIFEST.write_text(data)
    print(f'wrote {MANIFEST.relative_to(ROOT)} ({len(files())} files, version {version()})')
    return 0
if __name__=='__main__':
    raise SystemExit(main())
