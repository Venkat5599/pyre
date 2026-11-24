# Day-one checks

Checks that decide whether Pyre is worth building. Checks 1 to 3 were run on 2026-11-14, check 4 on 2026-11-24. Results below are the real outputs.

## 1. A key contribution runs in a browser

`browser-contribution/` holds a test circuit (`chain.circom`, a chain of 250 Poseidon hashes) and the page used to run snarkjs in the browser.

| Step | Result |
| --- | --- |
| Circuit size | 129,250 constraints (larger than most app circuits in the field) |
| Stage one | public perpetual powers-of-tau file `ppot_0080_17.ptau` (151 MB) |
| Proving key size | 55 MB |
| Contribution in Node (Apple M5, 10 cores) | 8.75 s |
| **Contribution inside Chrome, single tab** | **62.9 s**, 55,097,016-byte key out |
| Re-checking the whole transcript (`snarkjs zkey verify`) | 16 s, lists every contributor, `ZKey Ok!` |

A phone will be slower than a laptop. For circuits this size expect a few minutes; the client recommends a laptop above a size threshold.

Side finding: the stage-one files many tutorials link to now return HTTP 403. The perpetual powers-of-tau files still download, so Pyre starts from those.

## 2. A real passkey signature verifies inside a Soroban contract

`passkey-on-soroban/` is a Soroban contract (SDK 29) that accepts only a WebAuthn signature whose challenge is exactly the contribution hash. The signature fixture (`webauthn.json`) was produced by Chrome's own WebAuthn stack with a virtual platform authenticator (ES256); a physical phone is the next step.

```
test test::a_real_passkey_signature_over_the_contribution_hash_verifies ... ok
test test::the_same_signature_cannot_be_reused_for_another_contribution - should panic ... ok
test test::a_tampered_signature_is_refused - should panic ... ok
test test::edited_client_data_is_refused - should panic ... ok
test test::a_different_passkey_is_refused - should panic ... ok
test result: ok. 5 passed; 0 failed
cpu instructions: 3054001
```

Run it: `cd experiments/passkey-on-soroban && cargo test -- --nocapture`

## 3. Keys can be read from live contracts and from shipped key files

`read-keys/read-onchain-vk.mjs` reads a verifier's keys straight from Stellar mainnet contract storage. Sample output from a live privacy-pool contract is in `read-keys/mainnet-vk-sample.json` (read at ledger 65,477,192): both verifying keys came back with every point.

`read-keys/count-contributions.mjs` reads the contribution list out of a `.zkey` file directly, no circuit or stage-one file needed. `count-repo-keys.py` ran it over every key file shipped in the sampled repos. Results: `read-keys/repo-key-contributions.jsonl` (other teams are listed as numbered projects; run the script on the same sample to see names).

| Of 18 repos with readable key files | Count |
| --- | --- |
| Key holds exactly **one** contribution | **15** |
| Key holds 3 to 4 contributions | 3 (two of them made by one setup script in the same repo; one of unknown origin) |

Two more things the live read showed, both now part of the checker design:

- Alpha and beta in a verifying key come from stage one, so the checker can tell whether an app used a public stage-one file or made its own.
- The sampled live contract lets an admin replace its verifying keys at any time. A good ceremony means nothing if one admin can swap the key afterwards, so the checker also reports "key replaceable by admin".

## 4. A single-person setup can be forged, and Stellar's own pairing check accepts it

`forgery-demo/` turns the threat into running code. The circuit says "I know a, with a·a = y". The claim **y = 5 is false**: 5 is a quadratic non-residue in the BN254 scalar field, so no witness exists and no honest prover can make a proof.

- **Key A**: no phase-2 contribution (delta = gamma, the setup mistake behind the first live Groth16 exploits; see `docs/EVIDENCE.md`).
- **Key B**: the same circuit after one honest phase-2 contribution whose secret was thrown away.

The forgery needs only the delta scalar: `A = alpha`, `B = beta + b·G2`, `C = delta⁻¹·(b·alpha − IC(y))`. For key A delta is 1. A person who ran phase 2 alone and kept their secret is in exactly the same position.

Real output of `./run.sh` (also in `forgery-demo/run-output.txt`):

```
key A: delta_2 == gamma_2 ? true
key B: delta_2 == gamma_2 ? false
honest proof, y = 9, key B: true
5 is a non-residue in Fr: true
FORGED proof of a false statement (y = 5), key A (no phase 2): true
same forgery, key B (one honest contribution): false
test test::the_same_forgery_fails_after_one_honest_contribution ... ok
test test::forged_proof_of_a_false_statement_passes_on_a_key_with_no_phase_2 ... ok
test test::an_honest_proof_of_a_true_statement_passes_with_the_contributed_key ... ok
test result: ok. 3 passed; 0 failed
```

The last four lines run the Groth16 equation through Soroban SDK 29's `bn254().pairing_check`, the `bn254_multi_pairing_check` host function Stellar apps verify with. The honest-proof test shows the harness accepts valid proofs, so the failed forgery on key B is the key doing its job, not an encoding error. The harness is test code for this demonstration; Pyre ships no verifier.

Run it: `cd experiments/forgery-demo && ./run.sh` (needs Node and Rust; keys are regenerated each run).

**Also checked:** none of the 38 key files in the 18 sampled projects has zero phase-2 contributions, and the sampled live mainnet contract has `delta != gamma`. Stellar's sampled keys have the one-person problem, not the no-person one. The checker reports both.
