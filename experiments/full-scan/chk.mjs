// Check whether a .zkey's delta can be recomputed by anyone.
// Usage: node chk.mjs key.zkey
// Prints delta_2 == gamma_2 (no phase 2 at all), and, if every phase-2 step is a public beacon,
// whether the beacon values stored in the file reproduce the key's delta (anyone can forge).
import * as snarkjs from "snarkjs";
import * as binFileUtils from "@iden3/binfileutils";
import { getCurveFromName, utils } from "ffjavascript";
import { rngFromBeaconParams } from "./node_modules/snarkjs/src/misc.js";
const { unstringifyBigInts } = utils;
const file = process.argv[2];
const vk = await snarkjs.zKey.exportVerificationKey(file);
const curve = await getCurveFromName(vk.curve);
const { G2, Fr } = curve;
const sameG2 = JSON.stringify(vk.vk_delta_2) === JSON.stringify(vk.vk_gamma_2);

const { fd, sections } = await binFileUtils.readBinFile(file, "zkey", 2);
await binFileUtils.startReadUniqueSection(fd, sections, 2);
const n8 = await fd.readULE32();
await binFileUtils.endReadSection(fd, true);
await binFileUtils.startReadUniqueSection(fd, sections, 10);
await fd.read(64);
const n = await fd.readULE32();
const steps = [];
for (let i = 0; i < n; i++) {
  await fd.read(n8 * 2 * 3); await fd.read(n8 * 4); await fd.read(64);
  const type = await fd.readULE32();
  const len = await fd.readULE32();
  const p = await fd.read(len);
  const s = { type: type === 0 ? "contribution" : "beacon" };
  let j = 0;
  while (j < p.length) {
    const id = p[j++];
    if (id === 1) { const l = p[j++]; s.name = new TextDecoder().decode(p.slice(j, j + l)); j += l; }
    else if (id === 2) { s.exp = p[j++]; }
    else if (id === 3) { const l = p[j++]; s.hash = p.slice(j, j + l); j += l; }
    else break;
  }
  steps.push(s);
}
await fd.close();

let recomputable = null;
if (n > 0 && steps.every(s => s.type === "beacon" && s.hash)) {
  let delta = Fr.one;
  for (const s of steps) delta = Fr.mul(delta, Fr.fromRng(await rngFromBeaconParams(s.hash, s.exp)));
  recomputable = G2.eq(G2.timesFr(G2.g, delta), G2.fromObject(unstringifyBigInts(vk.vk_delta_2)));
}
console.log(JSON.stringify({ file: file.split("/").pop(), curve: vk.curve, steps: steps.map(s => s.type), delta_equals_gamma: sameG2, delta_recomputable_from_public_beacon: recomputable }));
process.exit(0);
