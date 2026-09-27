"""Keep the installed manifest until a genuinely new candidate passes preflight."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from validation_rules import require_candidate

ROOT=Path(__file__).resolve().parent

def main():
    # Keep permanent evidence even if candidate generation or validation fails.
    snapshot=Path(tempfile.mkdtemp(prefix='so4-installed-build-'))/'build'
    shutil.copytree(ROOT/'build',snapshot)
    print('Installed payload backup:',snapshot,flush=True)
    def run(*args):
        subprocess.run([sys.executable,'-X','utf8',*args],cwd=ROOT,check=True)
    try:
        run('build_patch.py')
        manifest=json.loads((ROOT/'build/manifest.json').read_text(encoding='utf-8'))
        require_candidate(manifest)
        run('verify_build.py')
        run('tools/probe_native_text.py')
    except BaseException:
        shutil.copytree(snapshot,ROOT/'build',dirs_exist_ok=True)
        raise
    run('patch_tool.py','restore','--build-dir',str(snapshot))
    try:
        run('patch_tool.py','apply')
    except BaseException:
        print('Apply failed. Preserved installed payload backup:',snapshot,flush=True)
        raise

if __name__=='__main__':main()
