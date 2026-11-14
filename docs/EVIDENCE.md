# Evidence

Every figure in the README and pitch, with where it comes from and how to re-derive it. This is the one file that names existing products and documents, on purpose.

## The field measurement

| Figure | Value | Source / method |
| --- | --- | --- |
| Projects in the two public Stellar ZK build fields | 443 (344 + 99) | DoraHacks project lists for SDF's "Real-World ZK" (June 2026) and "ZK Gaming" (Feb 2026) build competitions, pulled through the DoraHacks API on 2026-11-14 |
| Of those, Circom projects with a public GitHub repo | 225 | Project descriptions mentioning Circom, with a github.com repo link |
| Sample scanned | 25 | 30 URLs drawn (the placed Circom projects plus a seeded random sample, seed 7, of the rest); 25 resolved to a single readable repo |
| Sample projects shipping Groth16 keys or setup scripts | 22 | Repo tree contains `.zkey` files or scripts calling `zkey new` / `groth16 setup` |
| Of those 22, projects with a multi-party ceremony | 0 | No ceremony transcript, no external contributors, no reference to a ceremony; setup scripts run every contribution on one machine |
| Projects generating stage one themselves | 8 of 22 | Scripts call `powersoftau new` instead of using the public stage-one files |
| Sample repos whose shipped `.zkey` files could be read | 18 | Every `.zkey` in the repo tree, contribution list read from section 10 of the file ([`../experiments/read-keys/`](../experiments/read-keys/)) |
| Of those 18, keys holding exactly one contribution | 15 | [`../experiments/read-keys/repo-key-contributions.jsonl`](../experiments/read-keys/repo-key-contributions.jsonl) |
| Keys holding 3-4 contributions | 3 | Two produced by a setup script in the same repo that runs every contribution locally; one of unknown origin |

Method: [`../scripts/scan-setups.py`](../scripts/scan-setups.py) reads each repo's file tree through the GitHub API, finds `.zkey` / `.ptau` files and setup scripts, and counts `zkey new`, `zkey contribute`, `zkey beacon` and `powersoftau new` calls. Re-run it with any list of repo URLs, one per line.

Note on entropy: several scripts pass a fixed entropy string. snarkjs mixes 64 fresh random bytes into any entropy it is given (`getRandomRng` in `snarkjs/src/misc.js`), so those keys cannot be recomputed by outsiders. The risk is the one-person setup, not a public exploit.

## Stellar's own statements

| Claim | Source |
| --- | --- |
| "for production use a real multi-party ceremony, not a single-contributor dev setup" | `stellar/stellar-docs`, `.mintlify/skills/zk-proofs/SKILL.md`, pitfalls section |
| The same file's walkthrough runs a single-contributor setup (`powersoftau new`, one `contribute`, `groth16 setup`) | same file, "Trusted setup" step |
| The on-chain UltraHonk verifier accepts non-ZK proofs only | same file; `NethermindEth/rs-soroban-ultrahonk` README |

## Stellar primitives Pyre uses

| Primitive | Protocol / date | Source |
| --- | --- | --- |
| secp256r1 signature verification (passkeys) | CAP-51, Protocol 21, mainnet 2024-06-18 | `stellar/stellar-protocol` core/cap-0051.md |
| BLS12-381 operations and pairing check | CAP-59, Protocol 22, mainnet 2024-12-05 | core/cap-0059.md |
| BN254 operations and pairing check | CAP-74, Protocol 25, mainnet 2026-01-22 | core/cap-0074.md |
| BN254 multi-scalar multiplication and field ops | CAP-80, Protocol 26, mainnet 2026-05-06 | core/cap-0080.md |
| Groth16 verifier examples on Soroban (BN254, BLS12-381) | — | `stellar/soroban-examples` `groth16_verifier` |

## Prior art and neighbours

| Neighbour | What it does | The gap it leaves on Stellar |
| --- | --- | --- |
| p0tion (`privacy-ethereum/p0tion`) | Generic phase-two ceremony coordinator | Nothing recorded on Stellar, no passkey signatures, not readable by Soroban contracts |
| `edenbd1/semaphore-stellar` | Port of Semaphore v4 to Soroban, reusing Ethereum's existing ceremony | Covers one fixed circuit; gives other teams no way to run their own |
| Stellar Community Fund directory (531 projects) | — | No project mentions a ceremony, trusted setup or proving keys (keyword pass + manual review, 2026-11-14) |
| Known Instaward recipients (18, from public posts) | — | None is a setup tool |
