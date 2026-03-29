const fs = require("fs");
const path = require("path");

const TrustLayer = artifacts.require("TrustLayer");
const JobLedger = artifacts.require("JobLedger");

module.exports = async function (deployer) {
  await deployer.deploy(TrustLayer);
  const tl = await TrustLayer.deployed();
  await deployer.deploy(JobLedger);
  const jl = await JobLedger.deployed();

  const out = {
    TrustLayer: tl.address,
    JobLedger: jl.address,
    note: "Backend me blockchain_interface.py (TrustLayer) aur job_ledger_interface.py (JobLedger) me yahi addresses paste karo.",
  };
  const jsonPath = path.join(__dirname, "..", "deployed-addresses.json");
  fs.writeFileSync(jsonPath, JSON.stringify(out, null, 2));
  console.log("\n=== Deployed ===\n", JSON.stringify(out, null, 2));
  console.log("\nSaved:", jsonPath);
};
