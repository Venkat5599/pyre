import json, os, re, subprocess, sys, urllib.request, shutil
GH = shutil.which("gh") or os.path.expanduser("~/.local/bin/gh")
rows = [json.loads(l) for l in open(sys.argv[1]) if l.startswith("{")]
out = []
os.makedirs("zk", exist_ok=True)
for r in rows:
    if not r.get("zkey_files"):
        continue
    repo = r["repo"]
    meta = json.loads(subprocess.run([GH, "api", f"repos/{repo}"], capture_output=True, text=True).stdout or "{}")
    br = meta.get("default_branch", "main")
    tree = json.loads(subprocess.run([GH, "api", f"repos/{repo}/git/trees/{br}?recursive=1"], capture_output=True, text=True).stdout or "{}")
    zks = [(t["path"], t.get("size", 0)) for t in tree.get("tree", []) if t["path"].endswith(".zkey")]
    zks = [z for z in zks if not re.search(r"(_0+|_init|0000)\.zkey$", z[0])] or zks  # prefer final keys
    res = {"repo": repo, "keys": []}
    for path, size in sorted(zks, key=lambda z: z[1])[:3]:
        if size > 300_000_000:
            res["keys"].append({"path": path, "skip": "too large"}); continue
        local = os.path.join("zk", repo.replace("/", "__") + "__" + path.replace("/", "__"))
        try:
            urllib.request.urlretrieve(f"https://raw.githubusercontent.com/{repo}/{br}/{path}", local)
            with open(local, "rb") as f:
                head = f.read(200)
            if head.startswith(b"version https://git-lfs"):
                res["keys"].append({"path": path, "skip": "git-lfs pointer"}); continue
            p = subprocess.run(["node", "contribs.mjs", local], capture_output=True, text=True, timeout=300)
            info = json.loads(p.stdout) if p.stdout.strip().startswith("{") else {"error": p.stderr[-200:]}
            res["keys"].append({"path": path, "contributions": info.get("contributions"), "names": [c["name"] for c in info.get("list", [])], "error": info.get("error")})
        except Exception as e:
            res["keys"].append({"path": path, "error": str(e)[:120]})
        finally:
            if os.path.exists(local): os.remove(local)
    print(json.dumps(res), flush=True)
    out.append(res)
json.dump(out, open("zkey_contribs.json", "w"), indent=1)
