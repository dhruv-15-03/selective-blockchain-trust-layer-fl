from web3 import Web3
import json
from eth_utils import to_checksum_address

# Connect to Ganache
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))

# Connection check (web3 v5: is_connected(), v6+: is_connected property)
try:
    if hasattr(w3, "is_connected"):
        ok = w3.is_connected() if callable(w3.is_connected) else w3.is_connected
        print("Blockchain connected:", ok)
except Exception as e:
    print("Blockchain check skipped:", e)

# Set default account (server acts as aggregator authority)
w3.eth.default_account = w3.eth.accounts[0]

# 🔹 Replace with your deployed contract address
contract_address = to_checksum_address("0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0")

# 🔹 Paste your ABI here (copy from trustLayer.json)
abi = [
    {
      "anonymous": False,
      "inputs": [
        {
          "indexed": False,
          "internalType": "address",
          "name": "client",
          "type": "address"
        }
      ],
      "name": "Blacklisted",
      "type": "event"
    },
    {
      "anonymous": False,
      "inputs": [
        {
          "indexed": False,
          "internalType": "address",
          "name": "client",
          "type": "address"
        }
      ],
      "name": "ClientRegistered",
      "type": "event"
    },
    {
      "anonymous": False,
      "inputs": [
        {
          "indexed": False,
          "internalType": "address",
          "name": "client",
          "type": "address"
        },
        {
          "indexed": False,
          "internalType": "uint256",
          "name": "round",
          "type": "uint256"
        },
        {
          "indexed": False,
          "internalType": "bytes32",
          "name": "hash",
          "type": "bytes32"
        }
      ],
      "name": "HashSubmitted",
      "type": "event"
    },
    {
      "anonymous": False,
      "inputs": [
        {
          "indexed": False,
          "internalType": "address",
          "name": "client",
          "type": "address"
        },
        {
          "indexed": False,
          "internalType": "uint256",
          "name": "newTrust",
          "type": "uint256"
        }
      ],
      "name": "TrustUpdated",
      "type": "event"
    },
    {
      "inputs": [],
      "name": "owner",
      "outputs": [
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "INITIAL_TRUST",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "PENALTY",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "THRESHOLD",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        }
      ],
      "name": "blacklisted",
      "outputs": [
        {
          "internalType": "bool",
          "name": "",
          "type": "bool"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "client",
          "type": "address"
        }
      ],
      "name": "getTrust",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "client",
          "type": "address"
        }
      ],
      "name": "penalizeClient",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "registerClient",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "uint256",
          "name": "round",
          "type": "uint256"
        },
        {
          "internalType": "bytes32",
          "name": "hash",
          "type": "bytes32"
        }
      ],
      "name": "submitHash",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        }
      ],
      "name": "trustScore",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        },
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        }
      ],
      "name": "updateHashes",
      "outputs": [
        {
          "internalType": "bytes32",
          "name": "",
          "type": "bytes32"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "client",
          "type": "address"
        }
      ],
      "name": "rewardClient",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "REWARD",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [],
      "name": "MAX_TRUST",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "anonymous": False,
      "inputs": [
        {
          "indexed": False,
          "internalType": "address",
          "name": "client",
          "type": "address"
        },
        {
          "indexed": False,
          "internalType": "uint256",
          "name": "newTrust",
          "type": "uint256"
        }
      ],
      "name": "ClientRewarded",
      "type": "event"
    }
] 

# Create contract instance
contract = w3.eth.contract(address=contract_address, abi=abi)


# ===================================================================
# Safe blockchain helpers — never silently swallow failures
# ===================================================================

def verify_owner():
    """Verify the server's default account is the contract owner."""
    try:
        owner = contract.functions.owner().call()
        server = w3.eth.default_account
        if owner.lower() != server.lower():
            print(f"WARNING: Server account {server} is NOT the contract owner {owner}")
            return False
        return True
    except Exception as e:
        print(f"Owner verification failed: {e}")
        return False


def safe_penalize(address: str) -> dict:
    """Penalize a client with full error tracking. Returns {ok, trust, error}."""
    try:
        addr = to_checksum_address(address)
        tx = contract.functions.penalizeClient(addr).transact()
        receipt = w3.eth.wait_for_transaction_receipt(tx)
        if receipt["status"] != 1:
            return {"ok": False, "trust": None, "error": "TX reverted"}
        new_trust = contract.functions.getTrust(addr).call()
        blacklisted = contract.functions.blacklisted(addr).call()
        return {"ok": True, "trust": new_trust, "blacklisted": blacklisted, "error": None}
    except Exception as e:
        return {"ok": False, "trust": None, "error": str(e)[:200]}


def safe_reward(address: str) -> dict:
    """Reward a client with full error tracking. Returns {ok, trust, error}."""
    try:
        addr = to_checksum_address(address)
        tx = contract.functions.rewardClient(addr).transact()
        receipt = w3.eth.wait_for_transaction_receipt(tx)
        if receipt["status"] != 1:
            return {"ok": False, "trust": None, "error": "TX reverted"}
        new_trust = contract.functions.getTrust(addr).call()
        return {"ok": True, "trust": new_trust, "error": None}
    except Exception as e:
        return {"ok": False, "trust": None, "error": str(e)[:200]}


def safe_get_trust(address: str, fallback: int = 0) -> int:
    """Get trust score with fallback on error."""
    try:
        return contract.functions.getTrust(to_checksum_address(address)).call()
    except Exception:
        return fallback


def safe_is_blacklisted(address: str) -> bool:
    """Check if address is blacklisted, defaults to False on error."""
    try:
        return contract.functions.blacklisted(to_checksum_address(address)).call()
    except Exception:
        return False