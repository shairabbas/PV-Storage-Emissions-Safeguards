"""Hash V5 and V6, verify frozen scientific inputs/results, map all copied files."""
from pathlib import Path
import csv
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/'Carbon_Storage_Study_submission_candidate_V5'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

def main():
    source=[]
    for p in sorted(q for q in SOURCE.rglob('*') if q.is_file()):
        source.append({'path':p.relative_to(SOURCE).as_posix(),
                       'bytes':p.stat().st_size,'sha256':sha(p)})
    source_record={'source':SOURCE.name,'file_count':len(source),'files':source}
    (ROOT/'audit/v6_source_manifest.json').write_text(json.dumps(source_record,indent=2)+'\n',encoding='utf-8')
    frozen={x['path']:x for x in source}
    pairs=[]
    for name,x in frozen.items():
        target=ROOT/name
        value=sha(target) if target.exists() else ''
        status='missing_in_v6' if not target.exists() else 'unchanged' if value==x['sha256'] else 'modified_v6'
        if name.startswith(('results/','data/','tables/','src/')) and status!='unchanged':
            raise AssertionError(f'Frozen scientific input/result changed: {name} ({status})')
        pairs.append({'relative_path':name,'v5_sha256':x['sha256'],'v6_sha256':value,'status':status})
    with (ROOT/'audit/v6_provenance_map.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(pairs[0]))
        writer.writeheader();writer.writerows(pairs)
    files=[]
    for p in sorted(q for q in ROOT.rglob('*') if q.is_file() and q.relative_to(ROOT).as_posix()!='audit/v6_final_manifest.json'):
        files.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
    report={'source':SOURCE.name,'source_file_count':len(source),
            'unchanged_copies':sum(x['status']=='unchanged' for x in pairs),
            'modified_only_in_v6':sum(x['status']=='modified_v6' for x in pairs),
            'omitted_copies':sum(x['status']=='missing_in_v6' for x in pairs),
            'v6_file_count':len(files),'files':files}
    (ROOT/'audit/v6_final_manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='files'}))

if __name__=='__main__': main()
