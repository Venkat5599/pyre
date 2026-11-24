"""Scan Stellar ZK repos: which proof system each uses, and how its shipped Groth16 keys were made.
Usage: python3 scan.py repos.txt results.jsonl   (one owner/repo per line; resumable)
Needs the GitHub CLI (gh) logged in, Node, and `npm ci` in this folder (for contribs.mjs)."""
import json, os, re, subprocess, sys, shutil, urllib.request, concurrent.futures as cf, threading
GH = shutil.which("gh") or os.path.expanduser("~/.local/bin/gh")
HERE = os.path.dirname(os.path.abspath(__file__))
lock = threading.Lock()

def gh(path):
    r = subprocess.run([GH, "api", path], capture_output=True, text=True)
    if r.returncode: return None
    try: return json.loads(r.stdout)
    except Exception: return None

def raw(repo, br, path, limit=400_000):
    try:
        with urllib.request.urlopen(f"https://raw.githubusercontent.com/{repo}/{br}/{path}", timeout=30) as f:
            return f.read(limit)
    except Exception: return b""

SCRIPT = re.compile(r"(\.sh|package\.json|Makefile|justfile|\.(m?js|ts|py|rs|toml|ya?ml|md))$")
SKIP = re.compile(r"node_modules|/dist/|/build/|\.min\.|target/|vendor/|/\.git/")
HINT = re.compile(r"script|setup|build|circuit|package\.json|Makefile|justfile|zk|prove|ceremony|trusted|readme", re.I)

def zkey_contribs(repo, br, path, size):
    if size > 150_000_000: return {"path": path, "skip": "too large"}
    local = os.path.join(HERE, "tmp", (repo + "__" + path).replace("/", "__"))
    os.makedirs(os.path.dirname(local), exist_ok=True)
    try:
        urllib.request.urlretrieve(f"https://raw.githubusercontent.com/{repo}/{br}/{path}", local)
        with open(local, "rb") as f: head = f.read(200)
        if head.startswith(b"version https://git-lfs"): return {"path": path, "skip": "git-lfs"}
        p = subprocess.run(["node", os.path.join(HERE, "contribs.mjs"), local], capture_output=True, text=True, timeout=300)
        info = json.loads(p.stdout) if p.stdout.strip().startswith("{") else {"error": p.stderr[-150:]}
        return {"path": path, "contributions": info.get("contributions"), "names": [c["name"] for c in info.get("list", [])], "types": [c["type"] for c in info.get("list", [])], "error": info.get("error")}
    except Exception as e: return {"path": path, "error": str(e)[:120]}
    finally:
        if os.path.exists(local): os.remove(local)

def scan(repo):
    meta = gh(f"repos/{repo}")
    if not meta: return {"repo": repo, "status": "unreadable"}
    repo = meta["full_name"]; br = meta["default_branch"]
    tree = gh(f"repos/{repo}/git/trees/{br}?recursive=1") or {}
    blobs = [(t["path"], t.get("size", 0)) for t in tree.get("tree", []) if t["type"] == "blob"]
    files = [p for p, _ in blobs]
    has = lambda rx: any(re.search(rx, f) for f in files)
    cargo = b"".join(raw(repo, br, f, 60_000) for f in files if f.endswith("Cargo.toml") and not SKIP.search(f))[:2_000_000].decode("utf8", "ignore")
    cand = [f for f in files if SCRIPT.search(f) and not SKIP.search(f) and HINT.search(f)][:60]
    text = ""
    for f in cand:
        t = raw(repo, br, f).decode("utf8", "ignore")
        if re.search(r"snarkjs|zkey|ptau|groth16|powersoftau|setup", t, re.I): text += f"\n### {f}\n" + t
    systems = []
    if has(r"\.circom$") or has(r"\.zkey$") or "snarkjs" in text: systems.append("circom/snarkjs")
    if has(r"(^|/)Nargo\.toml$") or has(r"\.nr$"): systems.append("noir")
    if "risc0" in cargo or has(r"(^|/)methods/guest/"): systems.append("risc0")
    if "sp1" in cargo.lower() and re.search(r"sp1[-_]", cargo): systems.append("sp1")
    if re.search(r"ark[-_]groth16|ark[-_]bn254", cargo): systems.append("arkworks")
    if has(r"\.go$") and re.search(r"gnark", text + "".join(files), re.I): systems.append("gnark")
    soroban_pairing = bool(re.search(r"bn254|pairing_check|bls12_381", cargo + text)) or "soroban" in cargo
    zkeys = [(p, s) for p, s in blobs if p.endswith(".zkey") and not SKIP.search(p)]
    final = [z for z in zkeys if not re.search(r"(_0+|_init|0000)\.zkey$", z[0])] or zkeys
    keys = [zkey_contribs(repo, br, p, s) for p, s in sorted(final, key=lambda z: z[1])[:3]]
    return {"repo": repo, "fork": meta.get("fork"), "parent": (meta.get("parent") or {}).get("full_name"),
            "pushed": meta.get("pushed_at"), "stars": meta.get("stargazers_count"), "systems": systems,
            "soroban": soroban_pairing, "zkey_files": len(zkeys), "ptau_files": sum(f.endswith(".ptau") for f in files),
            "setup_calls": len(re.findall(r"zkey new|groth16 setup|zKey\.newZKey|groth16\.setup|newZKey", text)),
            "contribute_calls": len(re.findall(r"zkey contribute|zKey\.contribute", text)),
            "beacon_calls": len(re.findall(r"zkey beacon|zKey\.beacon", text)),
            "own_phase1": bool(re.search(r"powersoftau new", text)),
            "public_phase1": bool(re.search(r"hermez|powersOfTau28|ppot|perpetual", text, re.I)),
            "keys": keys}

if __name__ == "__main__":
    repos = [l.strip() for l in open(sys.argv[1]) if "/" in l]
    done = set()
    if os.path.exists(sys.argv[2]):
        done = {json.loads(l)["in"] for l in open(sys.argv[2]) if l.strip()}
    todo = [r for r in repos if r not in done]
    print(f"{len(todo)} to scan", flush=True)
    def job(r):
        try: res = scan(r)
        except Exception as e: res = {"repo": r, "status": "error", "error": str(e)[:150]}
        res["in"] = r
        with lock:
            with open(sys.argv[2], "a") as f: f.write(json.dumps(res) + "\n")
        return r
    with cf.ThreadPoolExecutor(8) as ex:
        for i, _ in enumerate(ex.map(job, todo), 1):
            if i % 25 == 0: print(i, flush=True)
