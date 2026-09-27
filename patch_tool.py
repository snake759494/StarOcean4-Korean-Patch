"""Apply, restore, or verify the locally built resource patch with hash preflight."""
from pathlib import Path
import argparse, hashlib, json, subprocess, os
from validation_rules import require_candidate

ROOT=Path(__file__).resolve().parent
def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['apply','restore','verify'])
    parser.add_argument('--game-dir',type=Path)
    parser.add_argument('--build-dir',type=Path,default=ROOT/'build')
    args=parser.parse_args()
    build=args.build_dir.resolve()
    manifest=json.loads((build/'manifest.json').read_text(encoding='utf-8'))
    if args.action=='apply': require_candidate(manifest)
    archive=(args.game_dir or Path(manifest['game_directory']))/manifest['game_archive']
    if args.action!='verify':
        running=subprocess.check_output(['tasklist','/FI','IMAGENAME eq StarOceanTheLastHope.exe','/FO','CSV','/NH'],creationflags=0x08000000)
        if b'StarOceanTheLastHope.exe' in running:
            raise RuntimeError('Close STAR OCEAN before applying or restoring the patch.')
    planned=[]; status=[]
    with archive.open('rb') as f:
        for item in manifest['resources']:
            original=(build/item['original']).read_bytes()
            patched=(build/item['patched']).read_bytes()
            assert len(original)==len(patched)==item['span']
            assert sha(original)==item['original_sha256'], 'Damaged original backup'
            assert sha(patched)==item['patched_sha256'], 'Damaged patch payload'
            assert 0<=item['offset'] and item['offset']+item['span']<=archive.stat().st_size
            f.seek(item['offset']); current=f.read(item['span']); h=sha(current)
            if h==item['original_sha256']: state='original'
            elif h==item['patched_sha256']: state='patched'
            else: raise RuntimeError(f"Unknown archive contents at {item['offset']:#x}; no writes performed.")
            status.append(state)
            target=patched if args.action=='apply' else original
            planned.append((item['offset'],current,target))
            print(f"pack {item['pack']}, entry {item['entry']}: {state}")
    if args.action=='verify': return
    # Preflight all regions before the first write; roll back on any write/verification failure.
    with archive.open('r+b') as f:
        try:
            for offset,current,target in planned:
                if current!=target: f.seek(offset); f.write(target)
            f.flush(); os.fsync(f.fileno())
            for offset,current,target in planned:
                f.seek(offset)
                assert f.read(len(target))==target, 'Read-back verification failed'
        except BaseException:
            for offset,current,target in planned: f.seek(offset); f.write(current)
            f.flush(); os.fsync(f.fileno())
            raise
    print('Patch applied and read-back verified.' if args.action=='apply' else 'Original resources restored and verified.')

if __name__=='__main__': main()
