"""Exercise apply/restore, idempotence, and refusal against a disposable archive."""
from pathlib import Path
import tempfile, json, shutil, subprocess, sys

root=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='so4-patch-test-') as tmp:
    base=Path(tmp); (base/'build').mkdir()
    shutil.copy2(root/'patch_tool.py',base/'patch_tool.py')
    shutil.copy2(root/'validation_rules.py',base/'validation_rules.py')
    manifest=json.loads((root/'build/manifest.json').read_text(encoding='utf-8'))
    pos=0; originals=[]; patches=[]
    for item in manifest['resources']:
        item['offset']=pos
        for key in ['original','patched']:
            shutil.copy2(root/'build'/item[key],base/'build'/item[key])
        originals.append((base/'build'/item['original']).read_bytes())
        patches.append((base/'build'/item['patched']).read_bytes())
        pos+=item['span']
    manifest['game_directory']=str(base)
    (base/'build/manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    archive=base/'0000.bin'; original=b''.join(originals); patched=b''.join(patches)
    archive.write_bytes(original)
    def run(action,ok=True):
        p=subprocess.run([sys.executable,str(base/'patch_tool.py'),action],capture_output=True)
        assert (p.returncode==0)==ok,(action,p.stdout,p.stderr)
    run('verify'); run('apply'); assert archive.read_bytes()==patched
    run('apply'); assert archive.read_bytes()==patched
    run('verify'); run('restore'); assert archive.read_bytes()==original
    run('restore'); assert archive.read_bytes()==original
    from validation_rules import payload_id
    (base/'localization').mkdir()
    failure=[{'payload_id':payload_id(manifest),'reason':'Disposable runtime-failure regression fixture'}]
    (base/'localization/known_failed_builds.json').write_text(json.dumps(failure),encoding='utf-8')
    run('apply',False); assert archive.read_bytes()==original
    run('restore'); assert archive.read_bytes()==original
    (base/'localization/known_failed_builds.json').write_text('[]',encoding='utf-8')
    altered=bytearray(original); altered[-17]^=0xff; archive.write_bytes(altered)
    run('apply',False); assert archive.read_bytes()==altered
print('PASS: apply/restore, read-back, idempotence, known failed payload refusal, and unknown-content refusal without writes.')
