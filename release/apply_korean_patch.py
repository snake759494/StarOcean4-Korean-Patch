"""STAR OCEAN - THE LAST HOPE 4K & Full HD Remaster  한글 패치 적용기

사용법: 게임을 종료한 뒤 이 프로그램을 실행하고 게임 폴더를 확인/입력합니다.
원본 복구: Steam 라이브러리 > 게임 속성 > 설치된 파일 > "게임 파일 무결성 확인".
"""
import sys, os, json, hashlib, subprocess, tempfile, struct
from pathlib import Path

HERE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
PAYLOAD = HERE/'payload'
XDELTA = HERE/'xdelta3.exe'
DEFAULT = Path(r'C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster')
sha = lambda b: hashlib.sha256(b).hexdigest()

APPID = '609150'

def steam_roots():
    """Steam install folders from the registry (current user first, then machine-wide)."""
    import winreg
    out = []
    for hive, key, val in ((winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam', 'SteamPath'),
                           (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam', 'InstallPath'),
                           (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Valve\Steam', 'InstallPath')):
        try:
            with winreg.OpenKey(hive, key) as k: out.append(Path(winreg.QueryValueEx(k, val)[0]))
        except OSError: pass
    return out

def find_game():
    """Locate the game through Steam's library list (libraryfolders.vdf) and the app manifest."""
    import re
    libs = []
    for root in steam_roots():
        libs.append(root)
        vdf = root/'steamapps'/'libraryfolders.vdf'
        try: text = vdf.read_text(encoding='utf-8', errors='ignore')
        except OSError: continue
        libs += [Path(p.replace('\\\\', '\\')) for p in re.findall(r'"path"\s+"([^"]+)"', text)]
    for lib in dict.fromkeys(libs):
        acf = lib/'steamapps'/f'appmanifest_{APPID}.acf'
        try: text = acf.read_text(encoding='utf-8', errors='ignore')
        except OSError: continue
        m = re.search(r'"installdir"\s+"([^"]+)"', text)
        if m and (lib/'steamapps'/'common'/m.group(1)/'0000.bin').exists():
            return lib/'steamapps'/'common'/m.group(1)
    return DEFAULT if (DEFAULT/'0000.bin').exists() else None

def ask_dir():
    if len(sys.argv) > 1 and (Path(sys.argv[1])/'0000.bin').exists(): return Path(sys.argv[1])
    found = find_game()
    while True:
        if found:
            print(f'게임 폴더: {found}')
            s = input('Enter = 이 폴더에 적용 / 다른 폴더라면 경로 입력: ').strip().strip('"')
            if not s: return found
        else:
            s = input('게임 폴더 경로를 입력하세요 (0000.bin 이 있는 폴더): ').strip().strip('"')
        d = Path(s)
        if (d/'0000.bin').exists(): return d
        print('그 폴더에 0000.bin 이 없습니다.')

def running():
    out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq StarOceanTheLastHope.exe', '/NH'], capture_output=True).stdout
    return b'StarOceanTheLastHope.exe' in out

def decode(src, patch):
    with tempfile.TemporaryDirectory() as t:
        a, o = Path(t)/'s', Path(t)/'o'; a.write_bytes(src)
        subprocess.run([str(XDELTA), '-d', '-f', '-s', str(a), str(PAYLOAD/patch), str(o)], check=True,
                       creationflags=0x08000000)
        return o.read_bytes()

def main():
    man = json.loads((PAYLOAD/'manifest.json').read_text(encoding='utf-8'))
    print('스타오션 4 한글 패치 적용기\n')
    game = ask_dir()
    if running(): sys.exit('게임이 실행 중입니다. 종료한 뒤 다시 실행하세요.')
    arcs = {0: game/'0000.bin', 1: game/'0001.bin'}
    for i, name in enumerate(('0000.bin', '0001.bin')):
        size = arcs[i].stat().st_size
        if size == man['patched_sizes'][name] and i == 0:
            with arcs[0].open('rb') as f:
                if sha(f.read(0xC0000)) == [x for x in man['items'] if x['mode'] == 'toc'][0]['new_sha256']:
                    sys.exit('이미 한글 패치가 적용되어 있습니다.')
        if size != man['original_sizes'][name]:
            sys.exit(f'{name} 크기가 원본과 다릅니다. Steam에서 "게임 파일 무결성 확인"을 한 뒤 다시 실행하세요.')
    items = man['items']
    # 1) verify every source region before writing anything
    print('원본 확인 중...')
    for n, it in enumerate(items, 1):
        with arcs[it['arc']].open('rb') as f:
            f.seek(it.get('source_offset', it['offset'])); b = f.read(it.get('source_length', it['length']))
        if sha(b) != it['old_sha256']:
            sys.exit('게임 데이터가 이 패치가 만들어진 버전과 다릅니다. 무결성 확인 후 다시 시도하세요.')
        print(f'\r  {n}/{len(items)}', end='', flush=True)
    print('\n패치 적용 중...')
    for n, it in enumerate(sorted(items, key=lambda x: ({'append': 0, 'inplace': 1, 'toc': 2}[x['mode']], x['offset'])), 1):
        path = arcs[it['arc']]
        with path.open('r+b') as f:
            f.seek(it.get('source_offset', it['offset'])); src = f.read(it.get('source_length', it['length']))
            new = decode(src, it['patch'])
            assert sha(new) == it['new_sha256'], it['patch']
            if it['mode'] == 'append':
                f.seek(0, 2); end = f.tell()
                assert end <= it['offset'], 'unexpected file size'
                f.write(bytes(it['offset'] - end))
            f.seek(it['offset']); f.write(new)
        print(f'\r  {n}/{len(items)}', end='', flush=True)
    print('\n\n완료! 게임 언어를 "일본어"로 설정하고 플레이하세요.')
    print('원본으로 되돌리려면 Steam의 "게임 파일 무결성 확인"을 사용하세요.')

if __name__ == '__main__':
    try: main()
    except SystemExit as e:
        if e.code: print('\n' + str(e.code))
    except Exception as e:
        print('\n오류:', e)
    try: input('\n엔터를 누르면 종료합니다.')
    except EOFError: pass

