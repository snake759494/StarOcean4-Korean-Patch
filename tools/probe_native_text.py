"""Run original EXE lookup/token instructions in isolated emulated memory.

This is an offline parser check, not a game-rendering acceptance test. The EXE
and game archives are read only. No game process is launched or modified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64
from unicorn.x86_const import *
from verify_slz import decode_native_slz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from localization.codec import messages

BASE = 0x140000000
MEM = 0x200000000
STOP = MEM + 0x1000
MANAGER = MEM + 0x2000
STATE = MEM + 0x4000
OBJECT = MEM + 0x5000
RESOURCE = MEM + 0x6000
RESULT = MEM + 0x7000
DATA = MEM + 0x10000
STACK = MEM + 0x3f00000

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--build-dir', type=Path, default=ROOT/'build')
    args = ap.parse_args()
    manifest = json.loads((args.build_dir/'manifest.json').read_text(encoding='utf-8'))
    exe = (Path(manifest['game_directory'])/'StarOceanTheLastHope.exe').read_bytes()
    sections = json.loads((ROOT/'tools/pe.json').read_text())['secs']
    uc = Uc(UC_ARCH_X86, UC_MODE_64)
    uc.mem_map(BASE, 0x6000000)
    uc.mem_map(MEM, 0x4000000)
    for _, va, _, raw, size in sections:
        uc.mem_write(BASE+va, exe[raw:raw+size])
    # Cookie verification is process-specific, unrelated to text decoding.
    # Stub only in the emulator; never alter the installed executable.
    uc.mem_write(BASE+0x84d110, b'\xc3')
    def put(addr, fmt, *values): uc.mem_write(addr, struct.pack(fmt, *values))
    def call(rva, *values):
        sp = STACK - 8
        put(sp, '<Q', STOP)
        uc.reg_write(UC_X86_REG_RSP, sp)
        for reg, val in zip((UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_R9), values):
            uc.reg_write(reg, val)
        uc.emu_start(BASE+rva, STOP, count=1000000)
        assert uc.reg_read(UC_X86_REG_RIP)==STOP, 'Native instruction limit exceeded'
        return uc.reg_read(UC_X86_REG_RAX)
    rows = []
    for pi, ei, selected in [(15,1,set(range(20117,20123))), (1438,5,set(range(21,34)))]:
        item = next(r for r in manifest['resources'] if (r['pack'],r['entry'])==(pi,ei))
        for kind in ('original','patched'):
            raw=(args.build_dir/item[kind]).read_bytes()
            d=decode_native_slz(raw)[0]
            sections=struct.unpack_from('<7I',d,24)
            uc.mem_write(DATA,d)
            put(MANAGER+0x218,'<Q',DATA)
            put(MANAGER+0x228,'<Q',DATA+16)
            put(MANAGER+0x240,'<Q',DATA+sections[2])
            put(RESOURCE+0x20,'<Q',DATA+sections[0])
            put(RESOURCE+0x48,'<I',0)
            put(OBJECT+0xa0,'<Q',RESOURCE)
            put(OBJECT+0xd4,'<f',34.0)
            put(OBJECT+0xdc,'<f',1.0)
            for mid, blob in messages(d).items():
                if mid not in selected: continue
                pointer=call(0x771d00, MANAGER,0,mid)
                assert DATA+sections[3]<=pointer<DATA+sections[4], (pi,ei,kind,mid,'lookup failed')
                put(STATE,'<Q',pointer)
                tokens=[]
                for _ in range(2048):
                    result=call(0x779880,OBJECT,STATE)
                    if result==0:break
                    token=struct.unpack('<I',uc.mem_read(STATE+8,4))[0]
                    tokens.append((result,token))
                else:raise AssertionError('Unterminated native text')
                glyphs=sum(t==2 for t,_ in tokens)
                assert glyphs>0, (pi,ei,kind,mid,'empty text')
                call(0x794730,OBJECT,pointer,RESULT)
                counted=struct.unpack('<5I',uc.mem_read(RESULT,20))
                assert counted[0]==glyphs, (pi,ei,kind,mid,'native parser disagreement')
                assert counted[4]==sum(v==0x4000 for _,v in tokens)
                rows.append(dict(resource=f'{pi}:{ei}',kind=kind,id=mid,glyphs=glyphs,newlines=counted[4]))
    report=dict(status='PASS',scope='Original executable message lookup and token/count routines only',
                runtime_verified=False,exe_sha256=hashlib.sha256(exe).hexdigest(),messages=rows)
    (args.build_dir/'native_text_probe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f'PASS: {len(rows)} original/patched messages through native lookup and parsers; rendering unverified.')

if __name__=='__main__':main()
