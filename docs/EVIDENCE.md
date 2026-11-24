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
| a16z "On-Chain Trusted Setup Ceremony" (`a16z/evm-powers-of-tau`) | A smart contract replaces the coordinator for a small powers-of-tau (phase 1) ceremony on Ethereum; parameters capped at about 64 KB | Phase 1 only, not per-circuit phase 2; Ethereum; no registry of deployed verifiers. Source: https://a16zfrontier.com/posts/article/on-chain-trusted-setup-ceremony |
| "Layer 2 Coordinated Trusted Setup for Continuous CRS Generation" (arXiv 2607.05776, Cyber-AI 2026) | Contributions applied sequentially through a contract using Circom's powers-of-tau implementation | Research prototype, phase 1, not on Stellar. Source: https://arxiv.org/abs/2607.05776 |
| "A Blockchain-based Protocol of Trusted Setup Ceremony" (ACM, doi 10.1145/3625078.3625083) | Smart contract verifies each CRS update | Academic design; not on Stellar; no passkeys or verifier check. Source: https://dl.acm.org/doi/fullHtml/10.1145/3625078.3625083 |

What these neighbours show: putting the ceremony record on a chain is a recognised direction, and all of it so far is phase 1 on Ethereum or in papers. Pyre's part is per-circuit phase 2 on Stellar, passkey-authorized contributions, a registry Soroban contracts can gate on, and a check of keys already deployed.

## Setup mistakes are being exploited in production

| Fact | Source |
| --- | --- |
| The first two known exploits of live ZK circuits (one taken by white-hat hackers for about $1.5M, one drained for 5 ETH) were Groth16 verifiers generated by snarkjs whose setup skipped the phase-2 contribution, so `delta_2 == gamma_2` | zkSecurity, "The First ZK Exploits Happened, and They Weren't What We Expected": https://blog.zksecurity.xyz/posts/groth16-setup-exploit |
| snarkjs `zkey new` initialises gamma_2 and delta_2 to the same G2 generator as a placeholder that phase 2 is expected to randomise | same post, quoting `src/zkey_new.js` |
| Reproduced here: with a no-phase-2 key, a proof of a false statement passes Stellar's own `bn254_multi_pairing_check`; after one honest contribution the same forgery fails | [`../experiments/forgery-demo/`](../experiments/forgery-demo/) |
| Checked on Stellar: none of the 38 key files in the 18 sampled projects is a zero-contribution key, and the sampled live mainnet contract has `delta != gamma`. The Stellar keys we sampled had one person's phase 2, not none | [`../experiments/read-keys/`](../experiments/read-keys/) |

## Demand on Stellar

| Signal | Source |
| --- | --- |
| A Stellar project's own issue: its shipped proving key has "no documented provenance"; "whoever ran it can forge proofs that pass the on-chain verifier"; the maintainer added a `SECURITY.md` documenting a single-contributor setup and lists the phase-2 transcript as still open | `Bitcoindefi/open-stellar-passport` issue #3: https://github.com/Bitcoindefi/open-stellar-passport/issues/3 |
| Public review of Stellar's private-payments reference implementation: "does not yet have a decentralized ceremony", called "a hard blocker for any production deployment" (forum post, secondary source; the implementation's own README says it is unaudited work in progress) | https://blockeden.xyz/forum/t/stellar-just-open-sourced-zk-private-payments-with-groth16-proofs-and-built-in-compliance-hooks-is-this-the-privacy-architecture-that-actually-satisfies-regulators/835 ; https://github.com/NethermindEth/stellar-private-payments |
