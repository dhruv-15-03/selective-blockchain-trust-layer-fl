async function main() {
  // Deploy TrustLayer (trust scores, hash commitments, penalties/rewards)
  const TrustLayer = await ethers.getContractFactory("TrustLayer");
  const trustLayer = await TrustLayer.deploy();
  await trustLayer.waitForDeployment();
  console.log("TrustLayer deployed to:", await trustLayer.getAddress());

  // Deploy JobLedger (complete job blocks with requirements, submissions, AI, decisions)
  const JobLedger = await ethers.getContractFactory("JobLedger");
  const jobLedger = await JobLedger.deploy();
  await jobLedger.waitForDeployment();
  console.log("JobLedger deployed to:", await jobLedger.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});