"""Summarise scan.py output. Usage: python3 analyze.py results.jsonl
A key counts as one-person if it holds at most one contribution that is not a public beacon:
a beacon is public randomness, so it does not hide the secret from the one person who contributed."""
import json, collections, sys

rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
ok = [r for r in rows if "systems" in r]
names = {r["repo"].lower() for r in ok}
uniq = [r for r in ok if not (r.get("fork") and r.get("parent") and r["parent"].lower() in names)]
zk = [r for r in uniq if r["systems"]]
groth = [r for r in zk if set(r["systems"]) & {"circom/snarkjs", "arkworks", "gnark"}]
other = [r for r in zk if set(r["systems"]) <= {"noir", "risc0", "sp1"}]

def people(k):
    t = k.get("types") or ["beacon" if "beacon" in (n or "").lower() else "contribution" for n in k.get("names", [])]
    return sum(1 for x in t if x == "contribution")

read = [r for r in groth if any(k.get("contributions") is not None for k in r["keys"])]
keys = lambda r: [k for k in r["keys"] if k.get("contributions") is not None]
best = {r["repo"]: max(people(k) for k in keys(r)) for r in read}
one = [r for r in read if best[r["repo"]] <= 1]
zero = [r for r in read if any(k["contributions"] == 0 for k in keys(r))]
# every phase-2 step is a beacon: delta comes only from beacon values stored in the file, so anyone can recompute it
beacon_only = [r for r in read if r not in zero and any(k["contributions"] > 0 and k.get("types") and people(k) == 0 for k in keys(r))]
multi = [r for r in read if best[r["repo"]] >= 2]

print(f"repos listed: {len(rows)}  readable: {len(ok)}  after dropping forks of listed repos: {len(uniq)}")
print(f"with a detectable proof system: {len(zk)}  {dict(collections.Counter(s for r in zk for s in r['systems']))}")
print(f"Groth16 family (per-circuit setup needed): {len(groth)}  |  Noir / RISC0 / SP1 only: {len(other)}")
print(f"Groth16 repos shipping a readable .zkey: {len(read)}")
print(f"  every key made by one person (<=1 non-beacon contribution): {len(one)} of {len(read)} ({100*len(one)/max(1,len(read)):.0f}%)")
print(f"  ship a key with zero contributions (delta == gamma, anyone can forge; confirm with chk.mjs): {len(zero)}")
print(f"  ship a key made only of public beacon steps (anyone can recompute delta; confirm with chk.mjs): {len(beacon_only)}")
print(f"  either case, forgeable by anyone: {len(zero) + len(beacon_only)}")
print(f"  2+ non-beacon contributions: {len(multi)}")
print(f"Groth16 repos pushed in 2026: {sum(1 for r in groth if (r.get('pushed') or '')[:4] == '2026')}")
print(f"phase 1: public Hermez/PPoT files {sum(r['public_phase1'] for r in groth)}  |  own 'powersoftau new' {sum(r['own_phase1'] for r in groth)}")
