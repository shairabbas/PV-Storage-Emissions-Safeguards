"""Hash reproducible code, inputs and outputs; omit external literature PDFs."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1<<20),b''):h.update(block)
    return h.hexdigest()

selected=[]
for folder in ('src','scripts','data','results','tables','figures'):
    selected.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
selected.extend(p for p in (ROOT/'audit').glob('*.json') if p.name!='final_manifest.json')
selected.extend(ROOT/name for name in ('NOVELTY_DECISION.md','REVISION_CHECKLIST.md',
    'REPRODUCE.md','RESPONSE_MATRIX.md','FINAL_DECISION.md','requirements.txt',
    'HIGHLIGHTS.txt','Highlights.docx','COVER_LETTER_DRAFT.md',
    'DATA_CODE_AVAILABILITY.md','AUTHOR_DECLARATION_CHECKLIST.md',
    'JOURNAL_GUIDANCE_AUDIT.md'))
selected.extend(ROOT/'literature'/name for name in ('PRIMARY_READING.md',))
selected.extend(ROOT/'manuscript'/name for name in ('main.tex','main.pdf','results_generated.tex',
    'supplement.tex','supplement.pdf','supplement_generated.tex'))
selected=sorted(set(selected))
files=[{'path':str(p.relative_to(ROOT)).replace('\\','/'),
        'bytes':p.stat().st_size,'sha256':digest(p)} for p in selected]
manifest={'scope':'Final author-review candidate derived from unchanged V3; historical V1–V3 preserved. Literature PDFs excluded from redistribution manifest.',
    'files':files,'file_count':len(files),'total_bytes':sum(f['bytes'] for f in files)}
(ROOT/'audit/final_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'files':manifest['file_count'],'bytes':manifest['total_bytes']}))
