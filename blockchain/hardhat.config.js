require("@nomicfoundation/hardhat-toolbox");

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: "0.8.24",
  networks: {
    ganache: {
      url: "http://127.0.0.1:7545",
      accounts: ["0x9d054ca29a9aca249809f68d35f773e7dc3d10c683b9ee46fb760add755c055d"]
    }
  }
};
