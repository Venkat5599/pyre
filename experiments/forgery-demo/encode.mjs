// Turn forge results into Soroban BN254 byte encodings (G1: x||y, G2: x.c1||x.c0||y.c1||y.c0, 32-byte big-endian).
import { readFileSync, writeFileSync } from "fs";
import * as snarkjs from "snarkjs";
import { getCurveFromName, utils } from "ffjavascript";
const { unstringifyBigInts } = utils;
const curve = await getCurveFromName("bn128");
const { G1, G2, Fr } = curve;
const h = (x) => BigInt(x).toString(16).padStart(64, "0");
const g1 = (p) => { const a = G1.toObject(G1.toAffine(p)); return h(a[0]) + h(a[1]); };
const g2 = (p) => { const a = G2.toObject(G2.toAffine(p)); return h(a[0][1]) + h(a[0][0]) + h(a[1][1]) + h(a[1][0]); };
const r = JSON.parse(readFileSync("result.json"));
const out = {};
for (const [name, file] of [["A", "keyA.zkey"], ["B", "keyB.zkey"]]) {
  const vk = unstringifyBigInts(await snarkjs.zKey.exportVerificationKey(file));
  const icx = G1.add(G1.fromObject(vk.IC[0]), G1.timesFr(G1.fromObject(vk.IC[1]), Fr.e(5n)));
  out[name] = {
    alpha: g1(G1.fromObject(vk.vk_alpha_1)), beta: g2(G2.fromObject(vk.vk_beta_2)),
    gamma: g2(G2.fromObject(vk.vk_gamma_2)), delta: g2(G2.fromObject(vk.vk_delta_2)), icx: g1(icx),
  };
}
// forged proof (built against key A); for key B the attacker can only reuse the same delta = 1 recipe
const p = unstringifyBigInts(r.forged_proof_key_A);
out.proof = { neg_a: g1(G1.neg(G1.fromObject(p.pi_a))), b: g2(G2.fromObject(p.pi_b)), c: g1(G1.fromObject(p.pi_c)) };
// honest proof of a TRUE statement (3^2 = 9) with key B, to prove the harness accepts valid proofs
const hp = await snarkjs.groth16.fullProve({ a: 3 }, "sqrt_js/sqrt.wasm", "keyB.zkey");
const pr = unstringifyBigInts(hp.proof);
const vkB = unstringifyBigInts(await snarkjs.zKey.exportVerificationKey("keyB.zkey"));
out.B9 = { ...out.B, icx: g1(G1.add(G1.fromObject(vkB.IC[0]), G1.timesFr(G1.fromObject(vkB.IC[1]), Fr.e(BigInt(hp.publicSignals[0]))))) };
out.honest = { neg_a: g1(G1.neg(G1.fromObject(pr.pi_a))), b: g2(G2.fromObject(pr.pi_b)), c: g1(G1.fromObject(pr.pi_c)) };
writeFileSync("soroban-fixture.json", JSON.stringify(out, null, 1));
console.log("ok");
await curve.terminate();
