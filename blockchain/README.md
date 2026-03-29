# Smart contracts (TrustLayer + JobLedger)

Pehle **Ganache** chalao: **HTTP `127.0.0.1:7545`** (is project ke backend jaisa).

---

## Option A — Truffle (`truffle-config.js` only)

Config sirf **`truffle-config.js`** me hai (do file se warning avoid karne ke liye alag `truffle.js` nahi rakha).

1. `cd blockchain` → `npm install` (sirf Hardhat deps; Truffle project me bundled nahi taaki Node 24 par install toot’ta na ho)
2. Ganache **127.0.0.1:7545** par chalao
3. Compile + migrate **`npx`** se (globally install karne ki zaroorat nahi):

```bash
npx truffle@5.11.5 compile
npx truffle@5.11.5 migrate --network development --reset
```

Ya `npm run compile:truffle` / `npm run migrate:ganache` (same commands `package.json` scripts se).

Agar `npx` slow ho to ek baar: `npm install -g truffle@5.11.5` phir seedha `truffle compile` / `truffle migrate`.

Deploy ke baad **`deployed-addresses.json`** root (`blockchain/`) me banega. Usme se addresses copy karke backend me daalo:

- `backend/server/blockchain_interface.py` → `contract_address` = **TrustLayer**
- `backend/server/job_ledger_interface.py` → `LEDGER_ADDRESS` = **JobLedger**

Phir backend restart — owner verification tab pass hogi jab Ganache ka **pehla account** hi deployer ho (Truffle default wahi use karti hai).

### Deploy fail: `invalid opcode` (TrustLayer / JobLedger)

Purana **Ganache** Ethereum **Shanghai** opcode (`PUSH0`) support nahi karta, jabki default Solidity bytecode use kar sakta hai. Is repo me **`evmVersion: "paris"`** set hai taaki classic Ganache par deploy chale.

Bytecode purana ho to dubara compile:

```bash
rm -rf build
npx truffle@5.11.5 compile --all
npx truffle@5.11.5 migrate --network development --reset
```

### µWS / `uws_darwin_arm64_137.node` warning

Truffle ke andar purani Ganache dependency **Node 24** ke saath poori tarah match nahi karti — warning aati hai, migrate **bahar wale** Ganache (7545) par phir bhi chal sakta hai. Permanent fix: **Ganache v7+** use karo ya deploy ke liye **Hardhat** (`npm run deploy:ganache:hh`).

---

## Option B — Hardhat (pehle se `scripts/deploy.js`)

1. Ganache **7545**
2. `cd blockchain` → `npm install`
3. `npm run deploy:ganache:hh`

**Dhyaan:** `hardhat.config.js` me `ganache` network ke liye jo private key hai, woh **Ganache ke us account se match honi chahiye** jisse tum deploy karna chahte ho (warna galat owner / insufficient funds). Agar confusion ho to **Truffle migrate** use karna asaan hai — woh seedha Ganache ke accounts use karti hai.

---

## Files

| File | Kaam |
|------|------|
| `truffle-config.js` | Official Truffle config (network + solc 0.8.20) |
| `truffle.js` | Purane tutorials ke naam se — `truffle-config.js` re-export |
| `migrations/1_deploy_trustlayer_jobledger.js` | Dono contracts deploy + JSON |
| `scripts/deploy.js` | Hardhat deploy (same do contracts) |
