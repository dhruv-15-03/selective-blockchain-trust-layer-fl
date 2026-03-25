async function main() {
  const TrustLayer = await ethers.getContractFactory("TrustLayer");
  const trustLayer = await TrustLayer.deploy();

  await trustLayer.waitForDeployment();

  console.log("Contract deployed to:", await trustLayer.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});