import { rpc, xdr, Address, scValToNative } from "@stellar/stellar-sdk";
const s = new rpc.Server("https://mainnet.sorobanrpc.com");
const key = xdr.LedgerKey.contractData(new xdr.LedgerKeyContractData({contract:new Address(process.argv[2]).toScAddress(),key:xdr.ScVal.scvLedgerKeyContractInstance(),durability:xdr.ContractDataDurability.fromName("persistent")}));
const r = await s.getLedgerEntries(key); const inst = r.entries[0].val.contractData.val.instance;
const out = {};
for (const e of inst.storage) { const k = scValToNative(e.key); const v = scValToNative(e.val);
  if (String(k).endsWith("Vk")) out[k] = Object.fromEntries(Object.entries(v).map(([a,b]) => [a, Array.isArray(b) ? b.map(x=>Buffer.from(x).toString("hex")) : Buffer.from(b).toString("hex")])); }
console.log(JSON.stringify({ledger: r.latestLedger, ...out}));
