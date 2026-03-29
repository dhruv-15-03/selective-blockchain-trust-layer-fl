"""
JobLedger blockchain interface — connects to the JobLedger smart contract
for storing complete job blocks (requirements, submissions, AI reviews, decisions).
"""
from web3 import Web3
from eth_utils import to_checksum_address
import json

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))
print("JobLedger blockchain connected:", w3.is_connected())

LEDGER_ADDRESS = to_checksum_address("0x5b1869D9A4C187F2EAa108f3062412ecf0526b24")

# ABI for JobLedger contract
LEDGER_ABI = json.loads("""[
    {"inputs":[],"stateMutability":"nonpayable","type":"constructor"},
    {"inputs":[{"internalType":"uint256","name":"jobId","type":"uint256"},{"internalType":"address","name":"client","type":"address"},{"internalType":"string","name":"title","type":"string"},{"internalType":"string","name":"description","type":"string"},{"internalType":"uint256","name":"totalBudget","type":"uint256"},{"internalType":"uint256","name":"totalSteps","type":"uint256"}],"name":"createJob","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"jobId","type":"uint256"},{"internalType":"uint256","name":"step","type":"uint256"},{"internalType":"string","name":"title","type":"string"},{"internalType":"string","name":"requirements","type":"string"},{"internalType":"uint256","name":"budget","type":"uint256"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"bytes32","name":"dataHash","type":"bytes32"}],"name":"commitRequirements","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"jobId","type":"uint256"},{"internalType":"uint256","name":"step","type":"uint256"},{"internalType":"address","name":"freelancer","type":"address"},{"internalType":"string","name":"githubUrl","type":"string"},{"internalType":"string","name":"commitSha","type":"string"},{"internalType":"bytes32","name":"dataHash","type":"bytes32"}],"name":"commitSubmission","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"jobId","type":"uint256"},{"internalType":"uint256","name":"step","type":"uint256"},{"internalType":"uint256","name":"aiScore","type":"uint256"},{"internalType":"bool","name":"aiPass","type":"bool"},{"internalType":"string","name":"aiMethod","type":"string"},{"internalType":"bytes32","name":"dataHash","type":"bytes32"}],"name":"commitAIReview","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"jobId","type":"uint256"},{"internalType":"uint256","name":"step","type":"uint256"},{"internalType":"bool","name":"approved","type":"bool"},{"internalType":"uint256","name":"paymentAmount","type":"uint256"},{"internalType":"bytes32","name":"dataHash","type":"bytes32"}],"name":"commitDecision","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"jobId","type":"uint256"}],"name":"getJob","outputs":[{"components":[{"internalType":"uint256","name":"jobId","type":"uint256"},{"internalType":"address","name":"client","type":"address"},{"internalType":"address","name":"freelancer","type":"address"},{"internalType":"uint256","name":"totalBudget","type":"uint256"},{"internalType":"uint256","name":"totalSteps","type":"uint256"},{"internalType":"uint256","name":"createdAt","type":"uint256"},{"internalType":"bool","name":"exists","type":"bool"}],"internalType":"struct JobLedger.JobRecord","name":"","type":"tuple"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"jobId","type":"uint256"},{"internalType":"uint256","name":"step","type":"uint256"}],"name":"getMilestone","outputs":[{"components":[{"internalType":"bytes32","name":"requirementsHash","type":"bytes32"},{"internalType":"uint256","name":"requirementsTimestamp","type":"uint256"},{"internalType":"bytes32","name":"submissionHash","type":"bytes32"},{"internalType":"uint256","name":"submissionTimestamp","type":"uint256"},{"internalType":"uint256","name":"aiScore","type":"uint256"},{"internalType":"bool","name":"aiPass","type":"bool"},{"internalType":"bytes32","name":"aiHash","type":"bytes32"},{"internalType":"uint256","name":"aiTimestamp","type":"uint256"},{"internalType":"bool","name":"decided","type":"bool"},{"internalType":"bool","name":"approved","type":"bool"},{"internalType":"uint256","name":"paymentAmount","type":"uint256"},{"internalType":"bytes32","name":"decisionHash","type":"bytes32"},{"internalType":"uint256","name":"decisionTimestamp","type":"uint256"}],"internalType":"struct JobLedger.MilestoneRecord","name":"","type":"tuple"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"totalJobs","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"jobId","type":"uint256"},{"indexed":true,"internalType":"address","name":"client","type":"address"},{"indexed":false,"internalType":"string","name":"title","type":"string"},{"indexed":false,"internalType":"string","name":"description","type":"string"},{"indexed":false,"internalType":"uint256","name":"totalBudget","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"totalSteps","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"timestamp","type":"uint256"}],"name":"JobCreated","type":"event"},
    {"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"jobId","type":"uint256"},{"indexed":true,"internalType":"uint256","name":"step","type":"uint256"},{"indexed":false,"internalType":"string","name":"title","type":"string"},{"indexed":false,"internalType":"string","name":"requirements","type":"string"},{"indexed":false,"internalType":"uint256","name":"budget","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"deadline","type":"uint256"},{"indexed":false,"internalType":"bytes32","name":"dataHash","type":"bytes32"},{"indexed":false,"internalType":"uint256","name":"timestamp","type":"uint256"}],"name":"RequirementsCommitted","type":"event"},
    {"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"jobId","type":"uint256"},{"indexed":true,"internalType":"uint256","name":"step","type":"uint256"},{"indexed":true,"internalType":"address","name":"freelancer","type":"address"},{"indexed":false,"internalType":"string","name":"githubUrl","type":"string"},{"indexed":false,"internalType":"string","name":"commitSha","type":"string"},{"indexed":false,"internalType":"bytes32","name":"dataHash","type":"bytes32"},{"indexed":false,"internalType":"uint256","name":"timestamp","type":"uint256"}],"name":"SubmissionCommitted","type":"event"},
    {"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"jobId","type":"uint256"},{"indexed":true,"internalType":"uint256","name":"step","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"aiScore","type":"uint256"},{"indexed":false,"internalType":"bool","name":"aiPass","type":"bool"},{"indexed":false,"internalType":"string","name":"aiMethod","type":"string"},{"indexed":false,"internalType":"bytes32","name":"dataHash","type":"bytes32"},{"indexed":false,"internalType":"uint256","name":"timestamp","type":"uint256"}],"name":"AIReviewCommitted","type":"event"},
    {"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"jobId","type":"uint256"},{"indexed":true,"internalType":"uint256","name":"step","type":"uint256"},{"indexed":false,"internalType":"bool","name":"approved","type":"bool"},{"indexed":false,"internalType":"uint256","name":"paymentAmount","type":"uint256"},{"indexed":false,"internalType":"bytes32","name":"dataHash","type":"bytes32"},{"indexed":false,"internalType":"uint256","name":"timestamp","type":"uint256"}],"name":"DecisionCommitted","type":"event"}
]""")

ledger_contract = w3.eth.contract(address=LEDGER_ADDRESS, abi=LEDGER_ABI)
w3.eth.default_account = w3.eth.accounts[0]


def ledger_create_job(job_id: int, client_addr: str, title: str, description: str, budget: float, total_steps: int) -> dict:
    try:
        tx = ledger_contract.functions.createJob(
            job_id,
            to_checksum_address(client_addr) if client_addr else w3.eth.accounts[0],
            title[:500],
            description[:1000],
            int(budget * 100),  # store as cents
            total_steps,
        ).transact()
        receipt = w3.eth.wait_for_transaction_receipt(tx)
        return {"ok": True, "tx": receipt.transactionHash.hex(), "block": receipt.blockNumber}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def ledger_commit_requirements(job_id: int, step: int, title: str, requirements: str, budget: float, deadline: int, data_hash: bytes) -> dict:
    try:
        tx = ledger_contract.functions.commitRequirements(
            job_id, step, title[:500], requirements[:2000], int(budget * 100), deadline, data_hash
        ).transact()
        receipt = w3.eth.wait_for_transaction_receipt(tx)
        return {"ok": True, "tx": receipt.transactionHash.hex(), "block": receipt.blockNumber}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def ledger_commit_submission(job_id: int, step: int, freelancer_addr: str, github_url: str, commit_sha: str, data_hash: bytes) -> dict:
    try:
        tx = ledger_contract.functions.commitSubmission(
            job_id, step,
            to_checksum_address(freelancer_addr) if freelancer_addr else w3.eth.accounts[0],
            github_url[:500], commit_sha[:40], data_hash
        ).transact()
        receipt = w3.eth.wait_for_transaction_receipt(tx)
        return {"ok": True, "tx": receipt.transactionHash.hex(), "block": receipt.blockNumber}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def ledger_commit_ai_review(job_id: int, step: int, ai_score: float, ai_pass: bool, ai_method: str, data_hash: bytes) -> dict:
    try:
        tx = ledger_contract.functions.commitAIReview(
            job_id, step, int(ai_score * 100), ai_pass, ai_method[:100], data_hash
        ).transact()
        receipt = w3.eth.wait_for_transaction_receipt(tx)
        return {"ok": True, "tx": receipt.transactionHash.hex(), "block": receipt.blockNumber}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def ledger_commit_decision(job_id: int, step: int, approved: bool, payment: float, data_hash: bytes) -> dict:
    try:
        tx = ledger_contract.functions.commitDecision(
            job_id, step, approved, int(payment * 100), data_hash
        ).transact()
        receipt = w3.eth.wait_for_transaction_receipt(tx)
        return {"ok": True, "tx": receipt.transactionHash.hex(), "block": receipt.blockNumber}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def ledger_get_job(job_id: int) -> dict:
    try:
        j = ledger_contract.functions.getJob(job_id).call()
        return {
            "jobId": j[0], "client": j[1], "freelancer": j[2],
            "totalBudget": j[3] / 100, "totalSteps": j[4],
            "createdAt": j[5], "exists": j[6],
        }
    except Exception as e:
        return {"exists": False, "error": str(e)[:200]}


def ledger_get_milestone(job_id: int, step: int) -> dict:
    try:
        m = ledger_contract.functions.getMilestone(job_id, step).call()
        return {
            "requirementsHash": "0x" + bytes(m[0]).hex(),
            "requirementsTimestamp": m[1],
            "submissionHash": "0x" + bytes(m[2]).hex(),
            "submissionTimestamp": m[3],
            "aiScore": m[4] / 100,
            "aiPass": m[5],
            "aiHash": "0x" + bytes(m[6]).hex(),
            "aiTimestamp": m[7],
            "decided": m[8],
            "approved": m[9],
            "paymentAmount": m[10] / 100,
            "decisionHash": "0x" + bytes(m[11]).hex(),
            "decisionTimestamp": m[12],
        }
    except Exception as e:
        return {"error": str(e)[:200]}
