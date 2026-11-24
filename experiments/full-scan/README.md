# Full scan: 374 Stellar ZK repositories

The first measurement ([`../read-keys/`](../read-keys/)) read 18 sampled projects. This one reads every Stellar ZK repository we could list, on 2026-11-24.

## Result

| Step | Count |
| --- | --- |
| Repositories listed | 374 (346 readable; 28 deleted or private) |
| After dropping forks of repositories already in the list | 345 |
| With a detectable proof system | 280 |
| Groth16 family (Circom/snarkjs, arkworks, gnark): needs a per-circuit setup | **189** |
| Noir, RISC Zero or SP1 only: no per-circuit setup, no ceremony needed | 91 |
| Groth16 repositories shipping a `.zkey` we could read | 77 |
| Every key made by one person (at most one contribution that is not a public beacon) | **74 of 77 (96%)** |
| Ship a key with **zero** contributions (`delta_2 == gamma_2`: anyone can forge, not only its maker), confirmed with `chk.mjs` | **6** |
| Ship a key made **only of public beacon steps**: the beacon values are stored in the file, so anyone can recompute delta and forge, confirmed with `chk.mjs` | **3** |
| Keys with two or more non-beacon contributions | 3 |
| Groth16 repositories pushed in 2026 | 186 |
| Phase 1 from the public Hermez / Perpetual Powers of Tau files vs. generated locally with `powersoftau new` | 62 vs. 67 |

A public beacon after a single contribution does not help: the beacon is public, so the one contributor still knows the final secret.

This corrects the earlier sample, where none of the 38 key files had zero contributions. The full set has 6 repositories that do (the forgery demo's key A), and 3 more whose keys are built only from public beacons, which is no better.

The reader fix in `contribs.mjs`: it takes the field size from the key's header, so BLS12-381 keys (48-byte field) are read correctly as well as BN254 ones. The first sample's reader assumed BN254, which kept the contribution count right but misread contribution types on BLS12-381 keys.

`chk.mjs` reports `delta_equals_gamma`. When every phase-2 step is a beacon, it also reports `delta_recomputable_from_public_beacon`, recomputing delta from the beacon hash and iteration count stored in the file.

## How the list was built

- Stellar ecosystem index (Stellar Raven): hackathon builds and repositories matching ZK, Groth16, Circom, Noir, privacy pool, private payments, ZK identity, RISC Zero, BN254 verifier, proof of reserves, shielded transfer.
- GitHub code search for Soroban's BN254 calls (`bn254().pairing_check`, `bn254_multi_pairing_check`, `env.crypto().bn254()`) and repository search for Soroban/Stellar plus ZK, Groth16 and Noir.

The list of repository names is not published, and `results-anonymised.jsonl` replaces names with shuffled ids and push dates with months. Nine of these repositories ship keys anyone can forge against, and their teams are being told privately first. The named list is shared with reviewers on request.

## Run it

```sh
cd experiments/full-scan
npm install
python3 scan.py repos.txt results.jsonl     # one owner/repo per line; resumable; needs gh logged in
python3 analyze.py results.jsonl
node chk.mjs some.zkey                      # delta_2 == gamma_2? delta recomputable from public beacons?
```

`scan.py` reads each repository's file tree, its build and setup scripts and Cargo manifests to find the proof system, then downloads every shipped `.zkey` (up to 150 MB, skipping Git LFS pointers) and reads its contribution list with `contribs.mjs`.
