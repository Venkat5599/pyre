<div align="center">

# PYRE

### Private apps on Stellar get their master key from many people at once, so no single laptop can ever fake a proof.

[![Status](https://img.shields.io/badge/status-design%20complete%20·%2030--day%20build-f59e0b)](#live-status)
[![Network](https://img.shields.io/badge/Stellar-Soroban-000000)](https://developers.stellar.org)
[![Proofs](https://img.shields.io/badge/Groth16-BN254%20·%20BLS12--381-7C3AED)](docs/PITCH.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)
![Stack](https://img.shields.io/badge/Soroban%20·%20Rust%20·%20snarkjs%20·%20passkeys-14151a)

**[ The pitch ↓ ](#the-20-second-pitch)** · **[ How it works ↓ ](#how-pyre-works)** · **[ Full technical pitch ↗ ](docs/PITCH.md)** · **[ Every figure, sourced ↗ ](docs/EVIDENCE.md)**

</div>

> **Status: design complete, build sprint starting.** Nothing below is deployed yet. Every row in [Live status](#live-status) says what exists today.

Almost every private app on Stellar proves things with Groth16, because today it is the only proof system on Stellar that is both cheap to check on-chain and actually hides the private inputs. Groth16 has one catch: each app needs a one-time key setup, and whoever runs that setup alone holds a secret that lets them fake any proof the app will ever accept. A privacy pool built that way could be drained by its own developer, and nobody on-chain could tell.

We opened the proving keys that 18 Stellar Groth16 projects ship, taken from two public Stellar ZK build fields (443 projects). **15 of the 18 keys hold exactly one contribution: one machine, one person.** Two of the other three were made by a single setup script in the same repo. Stellar's own ZK docs say production apps need "a real multi-party ceremony, not a single-contributor dev setup", and no tool for doing that exists on Stellar.

This is not theoretical. The first two exploits of live ZK apps anywhere were Groth16 keys with a skipped setup step. We reproduced that forgery against Stellar's own BN254 pairing check, and showed one honest contribution stops it ([`experiments/forgery-demo/`](experiments/forgery-demo/)).

Pyre is the safety seal for those keys: the public makes the key together, every step is recorded on Stellar, and anyone can check the result.

```
ONE LAPTOP  ->  one person can fake every proof
PYRE        ->  everyone who joins must collude to fake one proof
                (and you can always join yourself)
```

## Live status

| Surface | Status | The evidence |
| --- | --- | --- |
| Design + mechanism | Done | [`docs/PITCH.md`](docs/PITCH.md) |
| Protocol spec: MPC, passkey auth, randomness, host functions | Done | [`docs/PROTOCOL.md`](docs/PROTOCOL.md) |
| Trust model, threat model, mainnet prerequisites, recovery | Done | [`docs/SECURITY.md`](docs/SECURITY.md) |
| Field measurement (15 of 18 shipped keys hold one contribution) | Done | [`docs/EVIDENCE.md`](docs/EVIDENCE.md), [`experiments/read-keys/`](experiments/read-keys/) |
| Browser contribution, 129,250-constraint circuit | Done: 62.9 s in one Chrome tab | [`experiments/README.md`](experiments/README.md) |
| Real passkey signature verified in a Soroban contract | Done: 5 of 5 tests pass | [`experiments/passkey-on-soroban/`](experiments/passkey-on-soroban/) |
| Verifying keys read from a live mainnet contract | Done | [`experiments/read-keys/mainnet-vk-sample.json`](experiments/read-keys/mainnet-vk-sample.json) |
| **Forgery demonstration: a false proof passes Stellar's own BN254 pairing check on a key with no phase 2, and fails after one honest contribution** | Done: 3 of 3 tests pass | [`experiments/forgery-demo/`](experiments/forgery-demo/) |
| Ceremony contract (Soroban) | Week 1 of the sprint | — |
| Browser contribution app | Week 2 | — |
| Seal registry, attestations, check page, forgery demonstration | Week 3 | — |
| Mainnet deploy + Pyre's first public ceremony | Week 4 | — |

## The 20-second pitch

A private app on Stellar is locked with a master key. Today one developer makes that key alone, so that one person could fake transactions forever. **Pyre lets many people make the key together, each from a browser tab.** Each person mixes in their own randomness and throws it away. As long as one of them was honest, nobody can ever fake a proof. Every step is written to Stellar and signed with the contributor's passkey, so anyone can check that an app's key was made safely, and any contract can refuse a key that was not.

If you don't trust anyone in the list, add your own contribution. Then the key is safe as long as you are.

## Table of contents

- [Live status](#live-status)
- [The 20-second pitch](#the-20-second-pitch)
- [What Pyre is NOT](#what-pyre-is-not)
- [The problem I set out to solve](#the-problem-i-set-out-to-solve)
- [How Pyre works](#how-pyre-works)
- [Architecture](#architecture)
- [Where the guarantee is enforced](#where-the-guarantee-is-enforced)
- [Attack → test](#attack--test)
- [Why Stellar is load-bearing](#why-stellar-is-load-bearing)
- [Who uses it](#who-uses-it)
- [Roadmap and acceptance criteria](#roadmap-and-acceptance-criteria)
- [Tech stack](#tech-stack)
- [Documentation](#documentation)
- [License](#license)

## What Pyre is NOT

- **Not a new proof system.** Multi-party key setups are a known practice in cryptography. What Pyre adds is doing it natively on Stellar: an on-chain contribution log, passkey-signed contributors, a key registry other contracts can check, and a checker for verifiers already deployed.
- **Not a privacy app itself.** Pyre holds no funds and sees no user data. It is the seal that makes the private apps people already build safe to trust.
- **Not new cryptography.** The ceremony is the published Groth16 phase-2 protocol (BGM17) run with snarkjs. Pyre adds the on-chain record, passkey authorization, the registry and the checks. Exact protocol: [`docs/PROTOCOL.md`](docs/PROTOCOL.md).
- **Not an auditor of circuits.** A safe key does not make a buggy circuit correct. Pyre answers one question, who could forge a proof, and answers it with a record anyone can re-check.

## The problem I set out to solve

- Groth16 keys come from two stages. Stage one is shared and public. Stage two is per-circuit, and whoever contributes to it alone knows the secret ("toxic waste") that forges proofs.
- Stellar's ZK docs walk builders through a single-contributor setup and then tell them to replace it with a real ceremony before production. There is no Stellar tool to do that, so the walkthrough is what ships.
- We read the contribution list inside every key file the sampled projects ship. 15 of 18 hold exactly one contribution, and 8 projects generated stage one themselves instead of reusing the public files.
- Live contracts often let an admin replace the verifying key later, which undoes any ceremony. The checker flags that too. Method and figures: [`docs/EVIDENCE.md`](docs/EVIDENCE.md).
- The apps at risk are the ones that matter most: privacy pools holding deposits, proof-of-reserve contracts, KYC and eligibility proofs.

## How Pyre works

1. **Open a ceremony.** A team uploads its compiled circuit. Pyre starts from the public stage-one files and writes the circuit hash and the opening key hash to the ceremony contract on Stellar.
2. **Contribute from a browser.** Each contributor's tab downloads the latest key, mixes in fresh randomness in a web worker, and uploads the new key. The randomness is wiped when the tab closes.
3. **Sign it with a passkey.** Each contributor has a passkey smart account. The contract calls `require_auth` on it for the exact previous and new key hashes; the account checks the device's WebAuthn signature with Stellar's native secp256r1 host function. The contract only accepts a contribution that builds on the current head.
4. **Seal it with a Stellar ledger.** Closing the ceremony and naming a future ledger N happen in one call. After N closes, its header hash is applied with `snarkjs zkey beacon` (2¹⁰ iterated hashes) as the final step. Anyone can reproduce it byte for byte.
5. **Register and attest.** The registry checks the key's points are on the curve and computes the key hash itself. Anyone who re-runs the transcript verification can attest to it on-chain. Any app contract can refuse a key that is not registered or not attested.
6. **Check any deployed app.** Paste a contract ID into the checker. It reads the contract's verifying key from the chain and says whether a Pyre ceremony produced it, with how many contributors, whether stage one was public, whether phase 2 was skipped entirely (delta = gamma, the exploited mistake), and whether an admin can still swap the key.

## Architecture

| Component | What it does |
| --- | --- |
| `pyre-ceremony` (Soroban) | Ordered, append-only contribution log per ceremony. Authorizes contributors through their passkey smart accounts (`require_auth`), enforces the previous-hash chain, the close window, the committed beacon ledger, and `fork` for recovery. |
| `pyre-registry` (Soroban) | Validates key points, computes the key hash on-chain, stores the ceremony record and the list of attesters. One read call for any contract that wants to gate on it. |
| Contribution app (web) | Verifies the previous step, runs the stage-two contribution in a web worker, signs with the passkey account, uploads the key to content-addressed storage. |
| Transcript verification | `snarkjs zkey verify` plus the beacon step, re-run by anyone from the public files and the on-chain log. Pyre does not reimplement it. |
| Checker (web) | Reads a deployed verifier's key over Stellar RPC and matches it against the registry. |

**What runs where.** The chain enforces order, signatures, no backdating and the beacon. The heavy math (checking each key really extends the last one) is re-run by anyone with snarkjs and recorded as on-chain attestations, because it is far too large for a contract. Trust and threat model: [`docs/SECURITY.md`](docs/SECURITY.md). Both halves are public, so neither has to be trusted.

## Where the guarantee is enforced

| Guarantee | Enforced by | Test |
| --- | --- | --- |
| A contribution must build on the previous one | `pyre-ceremony` previous-hash check | planned |
| Each contribution is authorized by the device that made it | `require_auth` on the contributor's passkey smart account (secp256r1) | planned |
| Nothing can be added after the ceremony closes | `pyre-ceremony` window check | planned |
| The final beacon was unknowable at close | beacon ledger committed before close | planned |
| Every key extends the last one correctly | client check before each contribution + public `snarkjs zkey verify` + attestations | planned |
| The registered key is the one submitted | key hash computed on-chain by `pyre-registry` | planned |
| A contract can refuse an unregistered key | `pyre-registry` lookup | planned |

## Attack → test

| The abuse | What answers it |
| --- | --- |
| Insert a contribution that skips the previous key | previous-hash check refuses it (planned test) |
| Replay one passkey signature on a different key | the signature covers the key hash, so it fails (planned test) |
| Slip in a contribution after closing | window check refuses it (planned test) |
| Pick the beacon after seeing the final key | beacon ledger must be committed before close (planned test) |
| Register a key that the ceremony did not produce | registry only accepts the finalised transcript's key; the verifier re-run exposes a mismatch (planned test) |
| One person poses as many contributors | does not break safety: one honest contributor is enough, and anyone can add their own (documented, by design) |
| Coordinator censors a contributor or withholds a file | `contribute` is permissionless through any RPC; files are content-addressed; `fork` continues from the last valid step (planned test) |
| Key with no phase-2 step (delta = gamma) used to forge a proof | `forged_proof_of_a_false_statement_passes_on_a_key_with_no_phase_2` shows the attack passes Stellar's pairing check; `the_same_forgery_fails_after_one_honest_contribution` shows one honest contribution stops it; the checker flags delta = gamma |

## Why Stellar is load-bearing

| Stellar feature | Host function / mechanism | Protocol | What it does for Pyre |
| --- | --- | --- | --- |
| Passkeys checked in contracts | `verify_sig_ecdsa_secp256r1` inside the passkey account's `__check_auth` | 21 | contributors sign with a fingerprint, no wallet or seed phrase |
| Built-in authorization | `require_auth_for_args`, host-managed nonces | base | each signature covers the exact hashes and cannot be replayed |
| Ledger order | `get_ledger_sequence` | base | no contribution can be backdated; the beacon ledger is fixed ahead of time |
| Key validation on-chain | `bls12_381_g1_is_on_curve`, `bls12_381_g2_is_on_curve`, subgroup checks; `bn254_g1_is_on_curve` | 22; 26 | the registry rejects malformed keys |
| Hashing | `compute_hash_sha256` | base | the registry computes the key hash itself |
| The proofs the seal protects | `bls12_381_multi_pairing_check` / `bn254_multi_pairing_check`, `bn254_g1_add`, `bn254_g1_mul`, Poseidon/Poseidon2 | 22 / 25 (BN254 MSM and field ops: 26) | apps verify with Stellar's own host functions; Pyre writes no verifier |

A Soroban app can call the registry at setup and refuse a key that one person made. A transcript on a website cannot be read by a contract. Full mapping: [`docs/PROTOCOL.md`](docs/PROTOCOL.md#8-stellar-host-functions-used).

## Who uses it

- Every Groth16 team on Stellar: privacy pools, private payments, proof of reserves, age, KYC and eligibility proofs. Two public Stellar ZK build fields alone held 225 Circom projects with public code.
- Teams heading to mainnet, who need a ceremony before real money arrives.
- Users and reviewers who want to check an app before trusting it: the checker answers in one paste.

The first sealed key is Pyre's own public ceremony, open to anyone, so the launch depends on no other team. Ceremonies for live apps follow it.

## Roadmap and acceptance criteria

Each week is done only when every criterion below is met and its evidence is public.

| Week | Ships | Accepted when |
| --- | --- | --- |
| 1 | `pyre-ceremony` contract | `cargo test` passes for: in-order accept, stale `prev_hash` refused, contribution without the contributor's authorization refused, contribution after `commit_beacon` refused, `commit_beacon` before `min_contributors` or with `N < current + delay` refused, `fork` from a past index; contract on testnet with 3 contributions visible in an explorer |
| 2 | Browser contribution app | 5 testnet contributions from at least 2 device types with platform passkeys; the client refuses to build on a tampered previous key; a network-capture test shows the contribution secret never leaves the worker; `snarkjs zkey verify` passes on the resulting chain |
| 3 | `pyre-registry`, attestations, check page | check page flags delta = gamma; registry rejects an off-curve key point and stores an on-chain-computed key hash; `attest` requires the attester's authorization; check page returns "sealed, N contributors, A attestations" for the rehearsal key and "no seal" for a single-person key |
| 4 | Mainnet + first public ceremony | every prerequisite in [`docs/SECURITY.md`](docs/SECURITY.md#6-mainnet-prerequisites) met; immutable contracts deployed; ceremony closed with a committed beacon ledger; final key reproduced byte-for-byte on 2 independent machines; at least 2 attestations; check page shows the seal |

## Tech stack

Soroban (Rust) for the ceremony and registry contracts · snarkjs for stage-two contributions, the beacon and transcript checks · passkey smart accounts (Stellar Smart Account Kit) with WebAuthn verified by Stellar's native secp256r1 host function · Stellar RPC for reads · content-addressed storage for key files · a static web client.

## Documentation

| Doc | Read it for |
| --- | --- |
| [`docs/PITCH.md`](docs/PITCH.md) | The full technical pitch: mechanism, demo, risks |
| [`docs/PROTOCOL.md`](docs/PROTOCOL.md) | The exact MPC, passkey authorization, randomness and Stellar host functions |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Guarantee, assumptions, trust and threat models, coordinator limits, mainnet prerequisites, recovery |
| [`docs/EVIDENCE.md`](docs/EVIDENCE.md) | Every figure in this README with its source and how to re-derive it |
| [`experiments/README.md`](experiments/README.md) | The three day-one checks and their real outputs |
| [`scripts/scan-setups.py`](scripts/scan-setups.py) | Repo scan for setup scripts and key files |

## License

MIT, see [`LICENSE`](LICENSE).
