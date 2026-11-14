// Read the contribution list straight out of a .zkey (section 10), no r1cs/ptau needed.
import * as binFileUtils from "@iden3/binfileutils";
const { fd, sections } = await binFileUtils.readBinFile(process.argv[2], "zkey", 2);
await binFileUtils.startReadUniqueSection(fd, sections, 10);
const csHash = await fd.read(64);
const n = await fd.readULE32();
const out = [];
for (let i = 0; i < n; i++) {
  // deltaG1 (64 or 2*n8), deltaG2, transcript(64), then params
  const n8 = 32;
  await fd.read(n8 * 2 * 3); await fd.read(n8 * 4); await fd.read(64);
  const type = await fd.readULE32();
  const paramLength = await fd.readULE32();
  const p = await fd.read(paramLength); let name = ""; let j = 0;
  while (j < p.length) { const id = p[j++]; if (id === 1) { const len = p[j++]; name = new TextDecoder().decode(p.slice(j, j + len)); j += len; } else if (id === 2) { j += 1 + 32; } else if (id === 3) { j += 4; } else break; }
  out.push({ type: type === 0 ? "contribution" : "beacon", name });
}
await fd.close();
console.log(JSON.stringify({ file: process.argv[2], contributions: n, list: out }));
