"""Verify read-only source, write copied-file provenance and V5 SHA-256 manifest."""
from pathlib import Path
import csv
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/'Carbon_Storage_Study_final_candidate_20261021'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

def main():
    frozen=json.loads((ROOT/'audit/v5_source_manifest.json').read_text())['files']
    records=[]
    missing_source=[]
    changed_source=[]
    for item in frozen:
        name=item['path']; source=SOURCE/name; copy=ROOT/name
        if not source.exists(): missing_source.append(name);continue
        if sha(source)!=item['sha256']: changed_source.append(name)
        records.append({'relative_path':name,'original_sha256':item['sha256'],
                        'v5_sha256':sha(copy) if copy.exists() else '',
                        'status':('missing_in_v5' if not copy.exists() else
                                  'unchanged' if sha(copy)==item['sha256'] else 'modified_v5')})
    if missing_source or changed_source:
        raise RuntimeError(f'Source changed/missing: {missing_source[:5]} {changed_source[:5]}')
    with (ROOT/'audit/v5_provenance_map.csv').open('w',newline='',encoding='utf-8') as out:
        w=csv.DictWriter(out,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    all_files=sorted(p for p in ROOT.rglob('*') if p.is_file() and
                     p.relative_to(ROOT).as_posix()!='audit/v5_final_manifest.json')
    manifest={'source':SOURCE.name,'source_files_verified':len(frozen),
        'source_files_unchanged':len([r for r in records if r['status']=='unchanged']),
        'source_files_modified_only_in_v5':len([r for r in records if r['status']=='modified_v5']),
        'v5_files_hashed':len(all_files),
        'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,
                  'sha256':sha(p)} for p in all_files]}
    (ROOT/'audit/v5_final_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k!='files'}))

if __name__=='__main__': main()
