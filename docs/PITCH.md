# Pyre — full technical pitch

## Problem

Groth16 is the proof system private apps on Stellar rely on: Stellar verifies it natively on BN254 (since Protocol 25) and BLS12-381 (since Protocol 22), and it hides private inputs. The Noir/UltraHonk verifier on Soroban accepts non-zero-knowledge proofs only, so it cannot be used for privacy today.

Groth16 needs a circuit-specific setup (stage two). The party that runs it learns a secret that can produce valid-looking proofs for false statements. If one person runs it, the whole app rests on that person, forever, with no on-chain trace.

Measured: we read the contribution list inside the key files 18 Stellar Groth16 projects ship. 15 hold exactly one contribution; two of the other three come from one setup script. Stellar's own ZK docs tell builders to run "a real multi-party ceremony" before production. No Stellar tool exists for it. Sources: [`EVIDENCE.md`](EVIDENCE.md).

## Why it cannot be done well today

- Generic ceremony tools exist outside Stellar, but they record nothing on Stellar, cannot be checked by a Soroban contract, and do not sign contributions with the passkeys Stellar users already hold.
- A team that wants to do it right today has to coordinate files by hand and publish a transcript nobody on-chain can reference.

## The guarantee

> A key registered in Pyre can only be forged if **every** contributor colluded, and anyone can add themselves as a contributor before close.

## Mechanism

1. **Open.** `open(circuit_hash, initial_key_hash, curve, min_contributors, closes_at)` on `pyre-ceremony`. The initial key comes from the public stage-one files, never a team-made stage one.
2. **Contribute.** The browser client fetches the latest key, runs the stage-two contribution in a web worker with fresh randomness, uploads the new key to content-addressed storage, and calls `contribute(id, contributor, prev_hash, new_hash, file_cid)`, authorized by the contributor's passkey smart account. Exact flow: [`PROTOCOL.md`](PROTOCOL.md#5-passkey-to-soroban-authorization).
3. **Contract checks.** `prev_hash` equals the current head; the contributor's passkey smart account authorizes the exact hashes through `require_auth` (its `__check_auth` verifies the WebAuthn signature with Stellar's native secp256r1 host function); the ceremony is still open. The head moves to `new_hash`.
4. **Beacon.** Closing the ceremony and committing `beacon_ledger = N` (at least `delay` ledgers ahead) happen in one call. After ledger N closes, its header hash is applied with `snarkjs zkey beacon` as the final contribution. The contract stores N; the hash is checked off-chain, since Soroban cannot read past ledger hashes. See [`PROTOCOL.md`](PROTOCOL.md#6-randomness).
5. **Finalise.** `finalize(id, vk_bytes, final_cid)` validates the key points and computes the key hash on-chain. Anyone who re-runs `snarkjs zkey verify` from the public files can `attest` to it.
6. **Gate.** `pyre-registry.lookup(vk_hash) -> {ceremony, contributors, beacon_ledger, transcript_hash}`. A privacy pool can call it in its constructor and refuse an unregistered key.
7. **Check.** The checker reads a deployed verifier contract over RPC (instance storage and contract code), extracts the verifying-key points, hashes them and looks them up. Output: "Pyre ceremony, N contributors, beacon ledger L" or "no ceremony on record", plus whether stage one was public (alpha and beta match a public stage-one file) and whether an admin can replace the key.

## Why Stellar is load-bearing

- Native secp256r1 verification makes passkey-signed contributions cheap and wallet-free.
- Ledger order makes contributions impossible to backdate or reorder after the fact.
- A future ledger hash is a public, unpredictable beacon.
- Soroban contracts can gate on the registry at deployment time; a transcript on a website cannot be read by a contract.

## Demo

1. Paste a live Stellar verifier contract into the checker: **red, no ceremony on record.**
2. Open a ceremony for its circuit. Five people contribute from their phones; each passkey prompt appears; the log grows on Stellar.
3. A contribution built on an old key is **refused**. A replayed signature is **refused**. A contribution after close is **refused**.
4. Ledger N closes; its hash seals the key. The transcript verifier re-runs and prints the same key hash.
5. Paste the sealed demo contract: **green, N contributors, A attestations, beacon ledger L.**

## Who pays / who uses

- Ecosystem infrastructure: free and open source, MIT.
- Users: every Groth16 team on Stellar (225 Circom projects with public code across two public Stellar ZK build fields), teams moving to mainnet, and anyone reviewing an app before depositing.
- First sealed key: Pyre's own public ceremony in week 4, open to anyone. Ceremonies for live apps follow it.

## Risks

- **The mechanism is known.** Multi-party setups are standard practice in cryptography. The new part is the Stellar-native log, passkey signatures, a contract-readable registry and the deployed-verifier checker.
- **Checker coverage.** Verifiers that take the key as a call argument instead of storing it need the checker to read recent invocations. Some contracts may embed keys in a layout the checker cannot parse; it then reports "unknown" rather than guessing.
- **Large keys.** Big circuits make multi-hundred-MB keys, which strain phones. The client warns and recommends a laptop above a size threshold.
- **Adoption.** A team can still ship a one-person key. Pyre makes the difference visible and gives contracts a way to refuse it.

## Day-one checks (run 2026-11-14)

1. **Browser contribution:** a 129,250-constraint circuit contributed in 62.9 s inside one Chrome tab (8.75 s in Node). Passed.
2. **Passkey on Soroban:** a real WebAuthn ES256 signature over the contribution hash verifies in a Soroban SDK 29 contract; replayed, tampered, edited and wrong-key cases are refused. 5 of 5 tests pass. Passed.
3. **Reading keys:** both verifying keys read from a live mainnet contract; contribution counts read from 18 shipped key files. Passed.

Details and outputs: [`../experiments/README.md`](../experiments/README.md).
