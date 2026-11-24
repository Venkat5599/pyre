# Pyre protocol

This file specifies exactly what Pyre runs: the multi-party computation, how a passkey becomes a Soroban authorization, where the randomness comes from, and which Stellar host functions are used. Security assumptions, the coordinator's limits and recovery live in [`SECURITY.md`](SECURITY.md).

> **Status:** specification for the 30-day build. The browser contribution and the in-contract passkey check were run on 2026-11-14 ([`../experiments/README.md`](../experiments/README.md)); everything else here is what the sprint builds.

## Contents

- [1. What is being computed](#1-what-is-being-computed)
- [2. The MPC: Groth16 phase 2](#2-the-mpc-groth16-phase-2)
- [3. Why one honest contributor is enough](#3-why-one-honest-contributor-is-enough)
- [4. The ceremony contract](#4-the-ceremony-contract)
- [5. Passkey to Soroban authorization](#5-passkey-to-soroban-authorization)
- [6. Randomness](#6-randomness)
- [7. Finalisation, registry and attestations](#7-finalisation-registry-and-attestations)
- [8. Stellar host functions used](#8-stellar-host-functions-used)

## 1. What is being computed

A Groth16 proving/verifying key pair for one circuit. Its "toxic waste" is the set of secret scalars used to build it: τ, α, β from phase 1 (shared by every circuit) and δ from phase 2 (per circuit). Anyone who knows them can make proofs for false statements that the verifier accepts.

Pyre does not run phase 1. Every ceremony starts from a **public perpetual powers-of-tau file** (the same `ppot_0080_*.ptau` series the day-one check used), whose own transcript is public. Pyre runs **phase 2**, the per-circuit part that, in the 18 Stellar keys we measured, was almost always done by one person.

## 2. The MPC: Groth16 phase 2

Pyre uses the phase-2 protocol from Bowe, Gabizon and Miers, *Scalable Multi-party Computation for zk-SNARK Parameters in the Random Beacon Model* (IACR ePrint 2017/1050), as implemented by snarkjs (`zkey new`, `zkey contribute`, `zkey beacon`, `zkey verify`). Pyre writes no new cryptography; it records, orders and authenticates the steps on Stellar.

**Initial key (step 0).** `snarkjs zkey new circuit.r1cs ppot.ptau k0.zkey` derives the circuit's key from phase 1 with δ = 1. The δ-dependent parts are:

- `[δ]₁`, `[δ]₂`
- the L query: `[(β·uᵢ(τ) + α·vᵢ(τ) + wᵢ(τ)) / δ]₁` for every private wire i
- the H query: `[τʲ·Z(τ) / δ]₁` for j < n−1

**Contribution j.** The contributor samples a fresh scalar δⱼ and updates:

```
[δ]₁ ← δⱼ·[δ]₁        [δ]₂ ← δⱼ·[δ]₂
L    ← δⱼ⁻¹·L          H    ← δⱼ⁻¹·H
```

so after k contributions δ = δ₁·δ₂·…·δₖ. They publish, with the new key, a **proof of knowledge of δⱼ**: a G1 point `s` and `s·δⱼ`, plus `r·δⱼ` in G2, where `r` is hashed to G2 from the transcript so far, `s` and `s·δⱼ`. Then δⱼ is erased.

**Checks for every step** (what `snarkjs zkey verify` runs, and what each contributor's client runs on the previous step before contributing):

1. Proof of knowledge: `e(s, r·δⱼ) = e(s·δⱼ, r)`.
2. δ really moved by δⱼ: `e([δ_prev]₁, r·δⱼ) = e([δ_new]₁, r)` and the same ratio in G2.
3. L and H were divided by the same δⱼ: a random linear combination ρ of the query points satisfies `e(Σρ·L_new, [δ_new]₂) = e(Σρ·L_prev, [δ_prev]₂)`, likewise for H.
4. Everything not involving δ matches what `zkey new` derives from the r1cs and the public phase-1 file.

A step that fails any check breaks the chain: the next client refuses to build on it (see recovery in [`SECURITY.md`](SECURITY.md#7-recovery-procedures)).

## 3. Why one honest contributor is enough

Final δ = δ_beacon · ∏ δⱼ. If even one δⱼ was sampled uniformly and erased, the product is uniform and unknown to everyone else, including a party that controls every other contributor, the coordinator and the storage. BGM17 proves the resulting parameters are secure with one honest phase-2 participant, assuming phase 1 had one honest participant, under the paper's stated model (a random beacon applied at the end, and hash functions modelled as random oracles).

**What that proof does not cover, stated plainly:**

- A dishonest phase 1. Pyre only starts from public phase-1 files and the checker reports whether a deployed key's α and β match one.
- A circuit that is itself wrong. Out of scope.
- A key the app's admin can swap later. The checker reports it.
- Not knowing *which* contributor was honest. The guarantee is "one of them"; a relying party that trusts none of them adds its own contribution (section 4 keeps that open to anyone).

**The threat, run on real bytes (done 2026-11-24).** With `[γ]₂ = [1]₂` as snarkjs produces, anyone who knows δ can choose any b and set `A = [α]₁`, `B = [β]₂ + b·[1]₂`, `C = δ⁻¹·(b·[α]₁ − IC(x))`. [`../experiments/forgery-demo/`](../experiments/forgery-demo/) does exactly this for a statement with no witness (y = 5 is not a square in the BN254 field): the forged proof passes Soroban's `bn254_multi_pairing_check` on a key with no phase 2 (δ = 1, the mistake behind the first live Groth16 exploits), and the same forgery fails after one honest contribution. Key C in the same demo is exactly the Stellar pattern: one person made the single phase-2 contribution and kept the value behind it. Its key looks normal (δ ≠ γ), yet its maker recomputes δ and the forged proof passes the same pairing check (4 of 4 tests pass).

## 4. The ceremony contract

Soroban, Rust. One instance holds many ceremonies; storage is persistent and append-only.

| Call | Who | Rule |
| --- | --- | --- |
| `open(opener, circuit_hash, k0_hash, ptau_hash, curve, min_contributors, delay)` | anyone (`opener.require_auth()`) | starts at `head = k0_hash` |
| `contribute(id, contributor, prev_hash, new_hash, file_cid)` | anyone, permissionless | `contributor.require_auth_for_args(id, prev_hash, new_hash, file_cid)`; refused unless `prev_hash == head` and the ceremony is open; then `head = new_hash`, index += 1 |
| `commit_beacon(id, ledger)` | opener | only after `min_contributors`; `ledger ≥ current + delay`; closes the ceremony to new contributions |
| `finalize(id, vk_bytes, final_cid)` | opener | only after `ledger` has closed; see section 7 |
| `fork(parent_id, at_index)` | anyone | opens a new ceremony whose `head` is the parent's hash at `at_index`; used for recovery |

Concurrent contributors race on `prev_hash`; the loser's transaction fails cleanly and their client re-bases on the new head.

## 5. Passkey to Soroban authorization

Contributors do not hold Stellar keys. Each one has a **passkey smart account**: a Soroban account contract (from the Stellar Smart Account Kit) whose signer is the secp256r1 public key of a WebAuthn credential on their device.

1. The client builds the `contribute` invocation and simulates it. The host returns the authorization entry for the contributor's account.
2. The client computes the **signature payload**: `SHA-256(HashIdPreimage::SorobanAuthorization { network_id, nonce, signature_expiration_ledger, invocation })`. The invocation includes `id`, `prev_hash`, `new_hash` and `file_cid`.
3. The payload is passed to `navigator.credentials.get()` as the WebAuthn **challenge**. The device asks for the fingerprint or face, and returns `authenticatorData`, `clientDataJSON` and an ECDSA P-256 signature.
4. The transaction is submitted. Soroban calls the account's `__check_auth(signature_payload, signature, contexts)`, which:
   - parses `clientDataJSON`, requires `type == "webauthn.get"` and `challenge == base64url(signature_payload)`;
   - requires the user-present and user-verified flags in `authenticatorData`;
   - computes `SHA-256(authenticatorData ‖ SHA-256(clientDataJSON))` and checks the signature with the host function `verify_sig_ecdsa_secp256r1` (low-S normalised).
5. The host consumes the nonce, so the authorization cannot be replayed, and the signed invocation binds the exact hashes, so it cannot be reused for another contribution.

A fee sponsor may wrap the transaction in a fee bump so contributors need no XLM. The sponsor cannot alter the signed arguments; it can only decline to sponsor, in which case the contributor submits through any RPC.

Day-one evidence: a real WebAuthn ES256 signature whose challenge is the contribution hash verified inside a Soroban SDK 29 contract; replayed, tampered, edited-client-data and wrong-key cases were refused ([`../experiments/passkey-on-soroban/`](../experiments/passkey-on-soroban/)). In the product that check lives in the passkey account's `__check_auth`, reached through `require_auth`, not in a custom auth scheme.

## 6. Randomness

**Contributor randomness.** δⱼ is derived inside snarkjs from 64 bytes of `crypto.getRandomValues` (the browser CSPRNG) mixed with entropy typed by the contributor. It exists only in a dedicated Web Worker's memory, is never written to storage or sent over the network, and is dropped when the worker terminates. The client's network calls carry only the new key file and its hash.

**Beacon.** BGM17's security proof assumes one final step from a public random beacon, so the last contributor cannot bias the output. Pyre's construction:

1. After `min_contributors`, the opener calls `commit_beacon(id, N)`. The contract requires `N ≥ current_ledger + delay` (default 720 ledgers, about one hour) and closes the ceremony in the same call. The last contribution is therefore fixed before ledger N exists.
2. After ledger N closes, `b = hash of the ledger header at sequence N`, read from Horizon (`/ledgers/N`) or any Stellar history archive.
3. `snarkjs zkey beacon kₗₐₛₜ.zkey final.zkey <b> 10` applies b through 2¹⁰ iterated SHA-256 rounds as the final contribution. It is deterministic: anyone with the transcript and ledger N gets a byte-identical `final.zkey`.

**Verifiable how.** Ledger header hashes are chained and signed through Stellar consensus and published in history archives, so b is checkable by anyone without trusting Pyre. Soroban exposes no host function that reads a past ledger's hash, so **the contract stores N and the claimed b, and the match is checked off-chain** by every verifier and by the check page.

**Limit.** The validators that close ledger N influence its contents and could in principle grind its hash. Iterated hashing raises that cost, and more importantly the safety of the key does not rest on the beacon: it rests on one honest contributor (section 3). The beacon only removes last-contributor bias.

## 7. Finalisation, registry and attestations

- `finalize(id, vk_bytes, final_cid)`: the contract checks the ceremony is closed and ledger N has passed, validates the verifying-key points (for BLS12-381 every G1 and G2 point with `bls12_381_g1_is_on_curve`, `bls12_381_g2_is_on_curve` and the subgroup checks; for BN254 the G1 points with `bn254_g1_is_on_curve`, since there is no BN254 G2 curve check host function, so BN254 G2 points are checked off-chain by the transcript verification), computes `vk_hash = SHA-256(vk_bytes)` itself with `compute_hash_sha256`, and stores `{id, vk_hash, contributor count, beacon ledger, final_cid}` in the registry. The hash is computed on-chain, not supplied.
- The contract cannot run the pairing checks in section 2 for a whole key (millions of group operations), so **binding `vk_bytes` to the transcript is verified off-chain.** To avoid resting that on the opener alone, anyone who re-runs `snarkjs zkey verify` and the beacon step can call `attest(id, attester)` with `attester.require_auth()`. The registry lists every attester account.
- `lookup(vk_hash)` returns the record and attesters. An app's contract can call it at setup and refuse a key that is not registered or has fewer attestations than it requires.
- The check page re-runs the transcript verification in the browser for keys small enough to do so, and otherwise shows the attestations and how to re-run it.

## 8. Stellar host functions used

Versions from the `soroban-env-common` 29.0.1 interface (`env.json`, `min_supported_protocol`).

| Host function | Protocol | Where Pyre uses it |
| --- | --- | --- |
| `require_auth` / `require_auth_for_args` (auth framework) | base | every contributor, opener and attester call |
| `verify_sig_ecdsa_secp256r1` | 21 | inside the passkey smart account's `__check_auth` |
| `compute_hash_sha256` | base | registry computes `vk_hash` on-chain |
| `get_ledger_sequence` | base | close window, beacon `N ≥ current + delay` |
| `bls12_381_g1_is_on_curve`, `bls12_381_g2_is_on_curve`, `bls12_381_check_g1_is_in_subgroup`, `bls12_381_check_g2_is_in_subgroup` | 22 | registry validates BLS12-381 keys |
| `bn254_g1_is_on_curve` | 26 | registry validates BN254 G1 key points |

What the **apps** a Seal protects use to verify proofs, and why Pyre supports both curves:

| Host function | Protocol |
| --- | --- |
| `bls12_381_multi_pairing_check`, `bls12_381_g1_add`, `bls12_381_g1_mul`, `bls12_381_g1_msm` | 22 |
| `bn254_multi_pairing_check`, `bn254_g1_add`, `bn254_g1_mul` | 25 |
| `poseidon_permutation`, `poseidon2_permutation` (hashing inside circuits/contracts) | 25 |
| `bn254_g1_msm`, `bn254_fr_*` | 26 |

Pyre itself performs no proof verification and writes no verifier.
