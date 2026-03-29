/**
 * Truffle — Ganache pe deploy ke liye.
 * Ganache: host 127.0.0.1, port 7545 (backend / web3 default ke saath match).
 */
module.exports = {
  networks: {
    development: {
      host: "127.0.0.1",
      port: 7545,
      network_id: "*",
    },
  },
  compilers: {
    solc: {
      version: "0.8.20",
      settings: {
        optimizer: { enabled: true, runs: 200 },
        // Ganache (classic) often runs pre-Shanghai EVM — default solc bytecode can use PUSH0
        // and fail with "invalid opcode" on deploy. "paris" avoids Shanghai-only opcodes.
        evmVersion: "paris",
      },
    },
  },
  contracts_directory: "./contracts",
  migrations_directory: "./migrations",
  contracts_build_directory: "./build/contracts",
};
