# Pyre security model

What Pyre guarantees, who it trusts for what, what an attacker can and cannot do, the coordinator's limits, and the conditions for mainnet. The protocol itself is in [`PROTOCOL.md`](PROTOCOL.md).

## Contents

- [1. The guarantee](#1-the-guarantee)
- [2. Assumptions](#2-assumptions)
- [3. Trust model](#3-trust-model)
- [4. Threat model](#4-threat-model)
- [5. Coordinator and managed ceremonies](#5-coordinator-and-managed-ceremonies)
- [6. Mainnet prerequisites](#6-mainnet-prerequisites)
- [7. Recovery procedures](#7-recovery-procedures)
- [8. What Pyre does not hold](#8-what-pyre-does-not-hold)

## 1. The guarantee

> A key sealed by Pyre can only be used to forge proofs if **every** phase-2 contributor kept their secret, and colluded. Anyone, including the relying party itself, can add a contribution before the ceremony closes.

The proof of that statement is BGM17 (IACR ePrint 2017/1050), section 3 of [`PROTOCOL.md`](PROTOCOL.md). Pyre's job is to make the conditions of that proof true and checkable: every step verified, nothing reordered or backdated, a beacon fixed before it could be known, and the final key bound to the record an app relies on.

## 2. Assumptions

| # | Assumption | How it is met or checked |
| --- | --- | --- |
| A1 | Phase 1 had at least one honest participant | Pyre only starts from public perpetual powers-of-tau files; `ptau_hash` is stored at `open`; the checker reports whether a deployed key's α, β match a public phase-1 file |
| A2 | At least one phase-2 contributor sampled δⱼ honestly and erased it | anyone can contribute; a relying party that trusts no listed contributor adds its own |
| A3 | Every step of the transcript passes the checks in PROTOCOL §2 | each client verifies the previous step before contributing; `snarkjs zkey verify` is re-run by attesters and by the check page |
| A4 | The app verifies with the registered key and cannot swap it | the checker reads the deployed key and reports whether an admin can replace it |
| A5 | Standard hardness assumptions for BN254 / BLS12-381 pairings and SHA-256 | out of Pyre's control |

The circuit being correct is **not** assumed or claimed.

## 3. Trust model

| Party | Trusted for | Not trusted for |
| --- | --- | --- |
| Each contributor | nothing individually; one of them being honest is enough | correctness (their step is verified) |
| Opener (app team) | calling `commit_beacon` and `finalize` on time | the key's correctness: `vk_hash` is computed on-chain, and the transcript binding is re-checked by attesters |
| Coordinator (Pyre's web app and storage) | availability only | ordering, authorization, content, beacon, registry entries |
| Fee sponsor | paying fees | the signed arguments (it cannot change them) |
| Stellar validators | ledger ordering and the beacon ledger's hash | the key's secrecy (rests on A2, not on the beacon) |
| Attesters | an independent re-run of the transcript, publicly signed | being honest individually; a relying party chooses how many and which attesters it requires |

No server holds a signing key for any user. Contributors' keys are passkeys on their own devices; the only Stellar accounts involved are their passkey smart accounts.

## 4. Threat model

| Attacker / failure | What they try | Outcome |
| --- | --- | --- |
| All contributors but one, colluding | learn the final δ | fails: needs the honest δⱼ (PROTOCOL §3) |
| A contributor | upload a key that does not extend the previous one, or skip the proof of knowledge | the next client's verification fails and it refuses to build on it; recovery §7.1 |
| A contributor | contribute on top of an old head | contract refuses: `prev_hash != head` |
| Anyone | replay a contributor's signature on another contribution | fails: the signature covers `prev_hash`, `new_hash`, `file_cid` and a nonce the host consumes |
| Anyone | add a contribution after close | contract refuses: ceremony closed at `commit_beacon` |
| Last contributor or opener | pick the beacon after seeing the final contribution | fails: N is committed in the same call that closes the ceremony, at least `delay` ledgers ahead |
| Validators | grind ledger N's hash | influences only the beacon; safety still rests on A2; 2¹⁰ iterated hashing raises the cost |
| Opener | register a key the ceremony did not produce | `vk_hash` is computed on-chain from the submitted key; the mismatch with the transcript is caught by any verifier and shows as missing attestations |
| Coordinator | inflate the contributor count with its own accounts (Sybil) | does not reduce safety (A2), but the count is **not** a security measure; the Seal lists the accounts so a relying party can look for one it trusts, or add its own |
| Coordinator | censor a contributor, withhold files, go offline | liveness only; §5 and §7 |
| Storage | serve a different file | files are content-addressed and the hash is on-chain; a wrong file fails verification |
| App admin | replace the verifying key after sealing | Pyre cannot stop it; the checker reports "key replaceable by admin" |
| Malicious client code | exfiltrate δⱼ | mitigated by open-source static client, reproducible builds and the option to contribute from the CLI; not fully preventable for a given contributor, which is why A2 needs only one |

## 5. Coordinator and managed ceremonies

The coordinator is Pyre's hosted web app, file pinning and optional fee sponsorship. A **managed ceremony** is the same contracts and the same rules, with the coordinator inviting contributors and keeping the queue moving.

**It cannot:** add, edit, reorder or remove a contribution; sign for anyone; choose or change the beacon; write a registry entry for a key the opener did not finalize; produce an attestation for anyone but itself.

**It can:** refuse to serve the web app, refuse to pin a file, refuse to sponsor fees, delay its queue, or add its own contributions.

**Limits that follow, and the answer to each:**

- *Censorship.* `contribute` is permissionless: anyone can submit directly through any Stellar RPC with their own account, using the open-source client run locally.
- *Withheld files.* Contributors keep their own output file and can pin it anywhere; the on-chain hash says which file is right. If a file is truly lost, §7.2.
- *Single point of liveness.* A ceremony is not bound to the coordinator: the static client plus public RPC plus content-addressed files are enough to continue or finish it.
- *Decentralisation is of safety, not of operations.* A managed ceremony is operationally centralised and cryptographically decentralised. The Seal says who contributed and who attested; it never asks anyone to trust the coordinator for the key.

## 6. Mainnet prerequisites

Pyre's contracts hold no funds and no user keys. Before they are deployed to mainnet in week 4, all of the following must be true:

1. Contracts have **no admin and no upgrade path**; a fix ships as a new, versioned deployment, and registry entries are immutable.
2. Every test in the ceremony and registry suites passes, including the refusal tests listed in the roadmap.
3. A full **testnet dress rehearsal**: a ceremony with at least 5 contributions from at least 2 device types, closed with a committed beacon, finalized and registered.
4. The rehearsal's final key is **reproduced byte-for-byte on 2 independent machines** from the public transcript and ledger N, and `snarkjs zkey verify` passes on both.
5. The forgery demonstration (PROTOCOL §3) passes on testnet: forged proof accepted for the single-person key, no δ available for the sealed key.
6. Every file of the rehearsal is pinned on at least 2 independent storage providers.
7. This threat model is re-read against the deployed code; any gap is fixed or written down before deployment, not after.

An independent security review of the contracts is planned after the sprint. Because the contracts custody nothing, a flaw can corrupt a Seal record but cannot move funds; the remedy is a new deployment and re-registration, which §7 covers.

## 7. Recovery procedures

1. **Invalid contribution found** (verification fails at step k): the next contributor's client refuses to build on it. Anyone calls `fork(id, k−1)`, which opens a new ceremony from the last valid head; contributions continue there. The broken ceremony is never finalized, so it never reaches the registry.
2. **File lost or withheld:** same as 1, forking from the last step whose file is available. Contributors who already went after the lost step contribute again on the fork.
3. **Coordinator offline:** run the static client locally against public RPC and content-addressed storage; nothing on-chain depends on the coordinator.
4. **Opener stops responding before `commit_beacon`:** anyone forks the ceremony and becomes the opener of the fork; past contributions remain on-chain and are reused by the fork.
5. **Wrong key registered:** shows as zero attestations and a failed transcript check on the check page. The opener (or anyone, via a fork) finalizes the correct key; relying contracts should require attestations, never a bare entry.
6. **Contract bug after mainnet:** deploy a fixed version; re-register affected keys from their unchanged public transcripts; the check page labels which deployment a record came from.
7. **Compromised contributor device:** no action needed for safety (A2 needs one honest contributor, not all); the contribution stays in the append-only log.

## 8. What Pyre does not hold

No user funds. No user private keys (passkeys stay on devices; smart accounts are owned by them). No personal data: a contribution is an account address, two hashes and a file identifier. No AI anywhere in the flow.
