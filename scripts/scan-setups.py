"""Scan Circom/Groth16 repos for how their proving keys were made.

Usage: python3 scripts/scan-setups.py urls.txt   (one https://github.com/owner/repo per line)
Needs the GitHub CLI (gh) logged in. Prints one JSON line per repo and writes scan-results.json.
"""
import json, re, subprocess, sys, base64, os, shutil
GH = shutil.which("gh") or os.path.expanduser("~/.local/bin/gh")
def gh(path):
    r = subprocess.run([GH, "api", path], capture_output=True, text=True)
    if r.returncode: return None
    try: return json.loads(r.stdout)
    except Exception: return None

urls = [l.strip() for l in open(sys.argv[1]) if l.strip().startswith("https://github.com/")]
out = []
for u in urls:
    m = re.match(r"https://github.com/([^/]+)/([^/#?]+)", u)
    if not m or m.group(1) == "orgs": continue
    owner, repo = m.group(1), m.group(2).removesuffix(".git")
    meta = gh(f"repos/{owner}/{repo}")
    if not meta: out.append({"repo": f"{owner}/{repo}", "status": "unreadable"}); continue
    br = meta["default_branch"]
    tree = gh(f"repos/{owner}/{repo}/git/trees/{br}?recursive=1") or {}
    files = [t["path"] for t in tree.get("tree", []) if t["type"] == "blob"]
    zkeys = [f for f in files if f.endswith(".zkey")]
    ptaus = [f for f in files if f.endswith(".ptau")]
    cand = [f for f in files if re.search(r"(\.sh|package\.json|Makefile|justfile|\.(m?js|ts|py|rs|toml))$", f)
            and not re.search(r"node_modules|/dist/|/build/|\.min\.|target/|vendor/", f)
            and re.search(r"script|setup|build|circuit|package\.json|Makefile|justfile|zk|prove|ceremony|trusted", f, re.I)]
    text = ""
    for f in cand[:60]:
        c = gh(f"repos/{owner}/{repo}/contents/{f}?ref={br}")
        if c and c.get("encoding") == "base64":
            try: t = base64.b64decode(c["content"]).decode("utf8", "ignore")
            except Exception: continue
            if "snarkjs" in t or "zkey" in t or "ptau" in t or "groth16" in t.lower():
                text += f"\n### {f}\n" + t
    contrib = len(re.findall(r"zkey contribute|zKey\.contribute|zkey\.contribute", text))
    beacon = len(re.findall(r"zkey beacon|zKey\.beacon|beacon", text))
    zknew = len(re.findall(r"zkey new|groth16 setup|zKey\.newZKey|groth16\.setup|newZKey", text))
    devptau = bool(re.search(r"powersoftau new", text))
    hermez = bool(re.search(r"hermez|powersOfTau28|ppot|perpetual", text, re.I))
    entropy_fixed = re.findall(r"-e[= ]?[\"']([^\"']{1,60})[\"']|entropy[\"']?\s*[:=]\s*[\"']([^\"']{1,60})", text)
    out.append({"repo": f"{owner}/{repo}", "zkey_files": len(zkeys), "ptau_files": len(ptaus),
                "setup_calls": zknew, "contribute_calls": contrib, "beacon": beacon,
                "own_phase1": devptau, "public_phase1": hermez,
                "hardcoded_entropy": [a or b for a, b in entropy_fixed][:3],
                "scanned_files": text.count("\n### ")})
    print(json.dumps(out[-1]), flush=True)
json.dump(out, open("scan-results.json", "w"), indent=1)
