// Read the contribution list straight out of a .zkey (section 10), no r1cs/ptau needed.
// Works for BN254 (n8 = 32) and BLS12-381 (n8 = 48) keys: the field size is read from the Groth16 header (section 2).
import * as binFileUtils from "@iden3/binfileutils";
const { fd, sections } = await binFileUtils.readBinFile(process.argv[2], "zkey", 2);
await binFileUtils.startReadUniqueSection(fd, sections, 2);
const n8 = await fd.readULE32();            // n8q: bytes per base-field element
await binFileUtils.endReadSection(fd, true);
await binFileUtils.startReadUniqueSection(fd, sections, 10);
await fd.read(64);                           // circuit hash
const n = await fd.readULE32();
const out = [];
for (let i = 0; i < n; i++) {
  // deltaAfter, g1_s, g1_sx (G1, 2*n8 each), g2_spx (G2, 4*n8), transcript (64), type, params
  await fd.read(n8 * 2 * 3); await fd.read(n8 * 4); await fd.read(64);
  const type = await fd.readULE32();
  const paramLength = await fd.readULE32();
  const p = await fd.read(paramLength); let name = ""; let j = 0;
  // snarkjs params: 1 = name (len + bytes), 2 = numIterationsExp (1 byte), 3 = beacon hash (len + bytes)
  while (j < p.length) { const id = p[j++]; if (id === 1) { const len = p[j++]; name = new TextDecoder().decode(p.slice(j, j + len)); j += len; } else if (id === 2) { j += 1; } else if (id === 3) { j += 1 + p[j]; } else break; }
  out.push({ type: type === 0 ? "contribution" : "beacon", name });
}
await fd.close();
console.log(JSON.stringify({ file: process.argv[2], curve_n8: n8, contributions: n, list: out }));
