"""Package only current verified payloads, source, and required build inputs."""
from pathlib import Path
import json,zipfile,hashlib,os
from validation_rules import require_runtime_acceptance
ROOT=Path(__file__).resolve().parent
manifest=json.loads((ROOT/'build/manifest.json').read_text(encoding='utf-8'))
require_runtime_acceptance(manifest,ROOT/'build')
report=json.loads((ROOT/'build/verification.json').read_text(encoding='utf-8'))
assert report['status']=='PASS'
assert report['translated_messages_checked']==sum(map(len,manifest['translations'].values()))
files={ROOT/name for name in ['README_KO.md','AGENTS.md','build_patch.py','verify_build.py','patch_tool.py','test_patch_tool.py','package_build.py','build_and_apply.cmd','apply_patch.cmd','restore_original.cmd']}
files.add(ROOT/'build_opening_repair.py')
files.add(ROOT/'validation_rules.py')
files.add(ROOT/'safe_build_and_apply.py')
files.add(ROOT/'build/runtime_acceptance.json')
baseline=json.loads((ROOT/'build_verified_426/manifest.json').read_text(encoding='utf-8'))
files.add(ROOT/'build_verified_426/manifest.json')
for item in baseline['resources']:
    for kind in ('original','patched'):files.add(ROOT/'build_verified_426'/item[kind])
for name in ['slz.py','slzenc.py','SlzOptimal.cs','SlzOptimal.exe','mcdlib.py','render.py','bc7enc.py','verify_slz.py','packs0.json','packs.json']:
    files.add(ROOT/'tools'/name)
for path in (ROOT/'localization').rglob('*'):
    if path.is_file() and path.suffix in ('.py','.json') and '__pycache__' not in path.parts: files.add(path)
for item in manifest['resources']:
    for kind in ('original','patched'):
        path=ROOT/'build'/item[kind]
        assert hashlib.sha256(path.read_bytes()).hexdigest()==item[kind+'_sha256']
        files.add(path)
for name in ['manifest.json','verification.json','font_render_preview.png','opening_preview.png','hangul_atlas.png']:
    files.add(ROOT/'build'/name)
target=ROOT/'StarOcean4_Hangul_Font_Test_Build.zip'
temp=target.with_suffix('.zip.new')
with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for path in sorted(files): archive.write(path,path.relative_to(ROOT).as_posix())
with zipfile.ZipFile(temp) as archive: assert archive.testzip() is None
os.replace(temp,target)
digest=hashlib.sha256(target.read_bytes()).hexdigest()
target.with_suffix('.zip.sha256').write_text(digest+'  '+target.name+'\n',encoding='ascii')
print(f'{target.name}: {target.stat().st_size:,} bytes, {len(files)} verified files, SHA-256 {digest}')
