"""Map traced file-read offsets back to KCAP pack entries.

Input : trace_bin.csv  (xperf dumper output filtered to 0000.bin / 0001.bin)
Output: which pack/entry each read touched, ranked by bytes read.
"""
import sys, io, os, json, re, bisect, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
os.chdir(r"C:\Users\Jay\so4_kr_patch_backup\tools")

CSV = 'trace_bin.csv'
rows = open(CSV, encoding='utf-8', errors='replace').read().splitlines()
print(f"lines: {len(rows)}")

# --- figure out the column layout empirically -------------------------------
evkinds = collections.Counter()
for ln in rows[:5000]:
    evkinds[ln.split(',')[0].strip()] += 1
print("event kinds:", dict(evkinds.most_common(10)))

hexnum = re.compile(r'^0x[0-9a-fA-F]+$')
def parse(ln):
    f = [x.strip() for x in ln.split(',')]
    if not f: return None
    ev = f[0]
    fname = next((x for x in f if '.bin' in x.lower()), None)
    if fname is None: return None
    proc = next((x for x in f if '.exe' in x.lower()), '')
    nums = [int(x, 16) for x in f if hexnum.match(x)]
    return ev, proc, fname, nums, f

# --- build pack/entry lookup -------------------------------------------------
def load(idx):
    packs = json.load(open(idx))
    tab = []                       # (abs_start, abs_end, pack_i, id, type, usize)
    for pi, pk in enumerate(packs):
        offs = sorted(e[4] for e in pk['e'])
        for a, b, c, s, eo in pk['e']:
            nxt = next((o for o in offs if o > eo), pk['tot'])
            tab.append((pk['off'] + eo, pk['off'] + nxt, pi, a, b, s))
    tab.sort()
    return tab, [t[0] for t in tab]

T1, S1 = load('packs.json')
T0, S0 = load('packs0.json')
print(f"entry tables: 0001.bin={len(T1)}  0000.bin={len(T0)}")

def locate(tab, starts, off):
    i = bisect.bisect_right(starts, off) - 1
    if i >= 0 and tab[i][0] <= off < tab[i][1]:
        return tab[i]
    return None

hit = collections.Counter()       # (file, pack, id, type) -> bytes
unmapped = collections.Counter()
nread = 0
for ln in rows:
    p = parse(ln)
    if not p: continue
    ev, proc, fname, nums, f = p
    if 'staroceanthelasthope' not in proc.lower(): continue
    if 'read' not in ev.lower(): continue
    if len(nums) < 2: continue
    which = '0000' if '0000.bin' in fname.lower() else '0001'
    tab, starts = (T0, S0) if which == '0000' else (T1, S1)
    # offset/size are the two numbers that make sense as file position + length
    cand = [n for n in nums if n < (40 << 30)]
    if not cand: continue
    off = max(cand)               # file offset is the largest plausible value
    size = min((n for n in nums if 0 < n <= (64 << 20)), default=0)
    nread += 1
    e = locate(tab, starts, off)
    if e: hit[(which, e[2], e[3], e[4])] += size
    else: unmapped[(which, off >> 24)] += size

print(f"\nread events by the game on the two archives: {nread}")
print(f"mapped entries touched: {len(hit)}")
print(f"\n{'file':<6}{'pack':>7} {'id':>4} {'type':>7}   bytes")
for (w, pi, a, b), n in hit.most_common(40):
    print(f"{w:<6}{pi:>7} {a:>4} 0x{b:04x}  {n:,}")
if unmapped:
    print(f"\nunmapped reads (offset>>24 buckets): {len(unmapped)}")
    for k, v in unmapped.most_common(10):
        print(f"   {k[0]}  ~0x{k[1]<<24:x}  {v:,} bytes")
json.dump({f"{w}|{pi}|{a}|{b}": n for (w, pi, a, b), n in hit.items()},
          open('trace_hits.json', 'w'), indent=1)
