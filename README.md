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

Pyre is that tool.

```
ONE LAPTOP  ->  one person can fake every proof
PYRE        ->  everyone who joins must collude to fake one proof
                (and you can always join yourself)
```

## Live status

| Surface | Status | The evidence |
| --- | --- | --- |
| Design + mechanism | Done | [`docs/PITCH.md`](docs/PITCH.md) |
| Field measurement (15 of 18 shipped keys hold one contribution) | Done | [`docs/EVIDENCE.md`](docs/EVIDENCE.md), [`experiments/read-keys/`](experiments/read-keys/) |
| Browser contribution, 129,250-constraint circuit | Done: 62.9 s in one Chrome tab | [`experiments/README.md`](experiments/README.md) |
| Real passkey signature verified in a Soroban contract | Done: 5 of 5 tests pass | [`experiments/passkey-on-soroban/`](experiments/passkey-on-soroban/) |
| Verifying keys read from a live mainnet contract | Done | [`experiments/read-keys/mainnet-vk-sample.json`](experiments/read-keys/mainnet-vk-sample.json) |
| Ceremony log contract (Soroban) | Week 1 of the sprint | — |
| Browser contribution client | Week 2 | — |
| Key registry + checker | Week 3 | — |
| First real ceremony for a live mainnet app | Week 4 | — |

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
- [Build plan](#build-plan)
- [Tech stack](#tech-stack)
- [Documentation](#documentation)
- [License](#license)

## What Pyre is NOT

- **Not a new proof system.** Multi-party key setups are a known practice in cryptography. What Pyre adds is doing it natively on Stellar: an on-chain contribution log, passkey-signed contributors, a key registry other contracts can check, and a checker for verifiers already deployed.
- **Not a privacy app.** Pyre holds no funds and sees no user data. It makes the private apps people already build safe to trust.
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
3. **Sign it with a passkey.** The contributor signs the new key's hash with their device passkey. The contract checks the signature with Stellar's native secp256r1 verification and only accepts a contribution that builds on the previous one.
4. **Seal it with a Stellar ledger.** The team names a future ledger number before closing. That ledger's hash, which nobody could know in advance, is applied as the final random beacon.
5. **Register the key.** The final verifying key's hash goes into the registry, with its contributor count, transcript hash and beacon ledger. Any verifier contract can call the registry and refuse to run on a key that is not there.
6. **Check any deployed app.** Paste a contract ID into the checker. It reads the contract's verifying key from the chain and says whether a Pyre ceremony produced it, with how many contributors, whether stage one was public, and whether an admin can still swap the key.

## Architecture

| Component | What it does |
| --- | --- |
| `pyre-ceremony` (Soroban) | Ordered, append-only contribution log per ceremony. Checks passkey signatures, the previous-hash chain, the open/closed window and the beacon ledger. |
| `pyre-registry` (Soroban) | Maps a verifying-key hash to its ceremony record. One read call for any contract that wants to gate on it. |
| Contribution client (web) | Runs the stage-two contribution in a web worker, signs with WebAuthn, uploads the key to content-addressed storage. |
| Transcript verifier (CLI) | Re-checks the whole ceremony math from the public files and the on-chain log. Anyone can run it. |
| Checker (web) | Reads a deployed verifier's key over Stellar RPC and matches it against the registry. |

**What runs where.** The chain enforces order, signatures, no backdating and the beacon. The heavy math (checking each key really extends the last one) is re-run by anyone with the transcript verifier, because it is far too large for a contract. Both halves are public, so neither has to be trusted.

## Where the guarantee is enforced

| Guarantee | Enforced by | Test |
| --- | --- | --- |
| A contribution must build on the previous one | `pyre-ceremony` previous-hash check | planned |
| Each contribution is signed by the device that made it | `pyre-ceremony` secp256r1 check | planned |
| Nothing can be added after the ceremony closes | `pyre-ceremony` window check | planned |
| The final beacon was unknowable at close | beacon ledger committed before close | planned |
| Every key extends the last one correctly | transcript verifier (public re-run) | planned |
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

## Why Stellar is load-bearing

- **Passkeys are checked natively.** Stellar verifies secp256r1 signatures in contracts, so a contributor's phone can sign their contribution and the chain checks it with no extra wallet.
- **Ledgers make the beacon and the ordering.** Ledger closes give every contribution a time nobody can rewrite, and a future ledger hash is a beacon nobody can predict.
- **Contracts can gate on it.** A privacy pool on Soroban can call the registry during setup and refuse to start on a key one person made.
- **It matches the proofs Stellar checks.** Both curves Stellar verifies natively, BN254 and BLS12-381, are supported end to end.

## Who uses it

- Every Groth16 team on Stellar: privacy pools, private payments, proof of reserves, age, KYC and eligibility proofs. Two public Stellar ZK build fields alone held 225 Circom projects with public code.
- Teams heading to mainnet, who need a ceremony before real money arrives.
- Users and reviewers who want to check an app before trusting it: the checker answers in one paste.

The first ceremony re-keys an existing Groth16 app that is already live on Stellar mainnet.

## Build plan

| Week | Ships |
| --- | --- |
| 1 | `pyre-ceremony` contract with passkey checks, window and beacon commitment, unit tests with real signatures, testnet deploy |
| 2 | Browser contribution client: web-worker contribution, WebAuthn signing, content-addressed upload, resume on reload |
| 3 | `pyre-registry`, transcript verifier CLI, checker page reading deployed verifiers |
| 4 | Mainnet deploy, first public ceremony for a live mainnet app with independent contributors, docs and a guide for other teams |

## Tech stack

Soroban (Rust) for the ceremony and registry contracts · snarkjs for stage-two contributions and transcript checks · WebAuthn passkeys verified with Stellar's native secp256r1 host function · Stellar RPC for reads · a static web client.

## Documentation

| Doc | Read it for |
| --- | --- |
| [`docs/PITCH.md`](docs/PITCH.md) | The full technical pitch: mechanism, demo, risks |
| [`docs/EVIDENCE.md`](docs/EVIDENCE.md) | Every figure in this README with its source and how to re-derive it |
| [`experiments/README.md`](experiments/README.md) | The three day-one checks and their real outputs |
| [`scripts/scan-setups.py`](scripts/scan-setups.py) | Repo scan for setup scripts and key files |

## License

MIT, see [`LICENSE`](LICENSE).
