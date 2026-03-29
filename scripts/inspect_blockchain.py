from web3 import Web3
from eth_utils import to_checksum_address
import json

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))
latest = w3.eth.block_number

CONTRACT_ADDR = "0xe78A0F7E598Cc8b0Bb87894B0F60dD2a88d6a8Ab"

# Known event signatures
event_sigs = {
    Web3.keccak(text="ClientRegistered(address)").hex(): "ClientRegistered",
    Web3.keccak(text="HashSubmitted(address,uint256,bytes32)").hex(): "HashSubmitted",
    Web3.keccak(text="TrustUpdated(address,uint256)").hex(): "TrustUpdated",
    Web3.keccak(text="Blacklisted(address)").hex(): "Blacklisted",
    Web3.keccak(text="ClientRewarded(address,uint256)").hex(): "ClientRewarded",
}

print("=" * 70)
print("GANACHE BLOCKCHAIN STATE")
print("=" * 70)
print(f"Chain ID:         {w3.eth.chain_id}")
print(f"Total Blocks:     {latest}")
print(f"Contract Address: {CONTRACT_ADDR}")
print(f"Server (Owner):   {w3.eth.accounts[0]}")
print("=" * 70)

tx_count = 0
for i in range(0, latest + 1):
    block = w3.eth.get_block(i, full_transactions=True)
    txs = block["transactions"]
    for tx in txs:
        tx_count += 1
        receipt = w3.eth.get_transaction_receipt(tx.hash)
        to_addr = tx["to"] if tx["to"] else "CONTRACT DEPLOYMENT"
        status = "SUCCESS" if receipt.status == 1 else "REVERTED"

        print(f"\nBlock #{i} | TX #{tx_count}")
        print(f"  Hash:     {tx.hash.hex()}")
        print(f"  From:     {tx['from']}")
        print(f"  To:       {to_addr}")
        print(f"  Gas Used: {receipt.gasUsed}")
        print(f"  Status:   {status}")

        if not tx["to"]:
            print(f"  Contract: {receipt.contractAddress}")

        for log in receipt.logs:
            if log.topics:
                sig = log.topics[0].hex()
                name = event_sigs.get(sig, f"Unknown({sig[:16]}...)")
                print(f"  EVENT -> {name}")
                # Decode data for known events
                data = log["data"]
                if isinstance(data, bytes):
                    data = data.hex()
                elif isinstance(data, str) and data.startswith("0x"):
                    data = data[2:]
                if name == "ClientRegistered":
                    addr = "0x" + data[24:64]
                    print(f"           client = {to_checksum_address(addr)}")
                elif name == "HashSubmitted":
                    addr = "0x" + data[24:64]
                    round_num = int(data[64:128], 16)
                    hash_val = "0x" + data[128:192]
                    print(f"           client = {to_checksum_address(addr)}")
                    print(f"           round  = {round_num}")
                    print(f"           hash   = {hash_val}")
                elif name in ("TrustUpdated", "ClientRewarded"):
                    addr = "0x" + data[24:64]
                    new_trust = int(data[64:128], 16)
                    print(f"           client    = {to_checksum_address(addr)}")
                    print(f"           new_trust = {new_trust}")
                elif name == "Blacklisted":
                    addr = "0x" + data[24:64]
                    print(f"           client = {to_checksum_address(addr)}")

print(f"\n{'=' * 70}")
print(f"TOTAL TRANSACTIONS: {tx_count}")
print(f"{'=' * 70}")
