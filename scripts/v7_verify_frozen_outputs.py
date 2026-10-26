"""Verify that V7 has not altered the V6 model inputs or saved outcomes."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / 'Carbon_Storage_Study_submission_candidate_V6'
FROZEN = ('src', 'data', 'results', 'tables')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    checked = 0
    mismatches = []
    for dirname in FROZEN:
        for old in (BASE / dirname).rglob('*'):
            if not old.is_file():
                continue
            checked += 1
            relative = old.relative_to(BASE)
            current = ROOT / relative
            if not current.is_file() or digest(old) != digest(current):
                mismatches.append(str(relative))
    report = {
        'baseline': str(BASE),
        'checked_file_count': checked,
        'frozen_directories': list(FROZEN),
        'mismatches': mismatches,
        'interpretation': 'Byte-level equality of V6 and V7 input, implementation and saved-output files; this does not validate the underlying science.'
    }
    (ROOT / 'audit/v7_frozen_output_verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'checked': checked, 'mismatches': len(mismatches)}))
    if mismatches:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
