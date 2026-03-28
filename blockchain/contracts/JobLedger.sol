// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title JobLedger
 * @notice Immutable on-chain record of complete job lifecycle.
 *         Each job gets a full block containing requirements, submission,
 *         AI analysis, and final decision — all permanently stored.
 *
 *         Data is stored in both:
 *         1. Contract storage (structs) — for on-chain reads
 *         2. Event logs — for efficient off-chain indexing
 */
contract JobLedger {

    address public owner;

    // ── Compact on-chain storage (hashes for verification) ──
    struct MilestoneRecord {
        bytes32 requirementsHash;
        uint256 requirementsTimestamp;
        bytes32 submissionHash;
        uint256 submissionTimestamp;
        uint256 aiScore;        // 0-10000 (2 decimals: 7523 = 75.23%)
        bool aiPass;
        bytes32 aiHash;
        uint256 aiTimestamp;
        bool decided;
        bool approved;
        uint256 paymentAmount;
        bytes32 decisionHash;
        uint256 decisionTimestamp;
    }

    struct JobRecord {
        uint256 jobId;
        address client;
        address freelancer;
        uint256 totalBudget;
        uint256 totalSteps;
        uint256 createdAt;
        bool exists;
    }

    mapping(uint256 => JobRecord) public jobs;
    mapping(uint256 => mapping(uint256 => MilestoneRecord)) public milestones;
    uint256 public totalJobs;

    // ── Events: full data stored permanently in logs (cheapest on-chain storage) ──

    event JobCreated(
        uint256 indexed jobId,
        address indexed client,
        string title,
        string description,
        uint256 totalBudget,
        uint256 totalSteps,
        uint256 timestamp
    );

    event RequirementsCommitted(
        uint256 indexed jobId,
        uint256 indexed step,
        string title,
        string requirements,
        uint256 budget,
        uint256 deadline,
        bytes32 dataHash,
        uint256 timestamp
    );

    event SubmissionCommitted(
        uint256 indexed jobId,
        uint256 indexed step,
        address indexed freelancer,
        string githubUrl,
        string commitSha,
        bytes32 dataHash,
        uint256 timestamp
    );

    event AIReviewCommitted(
        uint256 indexed jobId,
        uint256 indexed step,
        uint256 aiScore,
        bool aiPass,
        string aiMethod,
        bytes32 dataHash,
        uint256 timestamp
    );

    event DecisionCommitted(
        uint256 indexed jobId,
        uint256 indexed step,
        bool approved,
        uint256 paymentAmount,
        bytes32 dataHash,
        uint256 timestamp
    );

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized");
        _;
    }

    // ── Phase 0: Create job + commit requirements ──
    function createJob(
        uint256 jobId,
        address client,
        string calldata title,
        string calldata description,
        uint256 totalBudget,
        uint256 totalSteps
    ) external onlyOwner {
        require(!jobs[jobId].exists, "Job already exists");

        jobs[jobId] = JobRecord({
            jobId: jobId,
            client: client,
            freelancer: address(0),
            totalBudget: totalBudget,
            totalSteps: totalSteps,
            createdAt: block.timestamp,
            exists: true
        });
        totalJobs++;

        emit JobCreated(jobId, client, title, description, totalBudget, totalSteps, block.timestamp);
    }

    function commitRequirements(
        uint256 jobId,
        uint256 step,
        string calldata title,
        string calldata requirements,
        uint256 budget,
        uint256 deadline,
        bytes32 dataHash
    ) external onlyOwner {
        require(jobs[jobId].exists, "Job not found");

        milestones[jobId][step].requirementsHash = dataHash;
        milestones[jobId][step].requirementsTimestamp = block.timestamp;

        emit RequirementsCommitted(jobId, step, title, requirements, budget, deadline, dataHash, block.timestamp);
    }

    // ── Phase 1: Freelancer submission ──
    function commitSubmission(
        uint256 jobId,
        uint256 step,
        address freelancer,
        string calldata githubUrl,
        string calldata commitSha,
        bytes32 dataHash
    ) external onlyOwner {
        require(jobs[jobId].exists, "Job not found");

        if (jobs[jobId].freelancer == address(0)) {
            jobs[jobId].freelancer = freelancer;
        }

        milestones[jobId][step].submissionHash = dataHash;
        milestones[jobId][step].submissionTimestamp = block.timestamp;

        emit SubmissionCommitted(jobId, step, freelancer, githubUrl, commitSha, dataHash, block.timestamp);
    }

    // ── Phase 2: AI Review ──
    function commitAIReview(
        uint256 jobId,
        uint256 step,
        uint256 aiScore,
        bool aiPass,
        string calldata aiMethod,
        bytes32 dataHash
    ) external onlyOwner {
        require(jobs[jobId].exists, "Job not found");

        MilestoneRecord storage ms = milestones[jobId][step];
        ms.aiScore = aiScore;
        ms.aiPass = aiPass;
        ms.aiHash = dataHash;
        ms.aiTimestamp = block.timestamp;

        emit AIReviewCommitted(jobId, step, aiScore, aiPass, aiMethod, dataHash, block.timestamp);
    }

    // ── Phase 3: Decision ──
    function commitDecision(
        uint256 jobId,
        uint256 step,
        bool approved,
        uint256 paymentAmount,
        bytes32 dataHash
    ) external onlyOwner {
        require(jobs[jobId].exists, "Job not found");

        MilestoneRecord storage ms = milestones[jobId][step];
        ms.decided = true;
        ms.approved = approved;
        ms.paymentAmount = paymentAmount;
        ms.decisionHash = dataHash;
        ms.decisionTimestamp = block.timestamp;

        emit DecisionCommitted(jobId, step, approved, paymentAmount, dataHash, block.timestamp);
    }

    // ── Read functions ──

    function getJob(uint256 jobId) external view returns (JobRecord memory) {
        require(jobs[jobId].exists, "Job not found");
        return jobs[jobId];
    }

    function getMilestone(uint256 jobId, uint256 step) external view returns (MilestoneRecord memory) {
        require(jobs[jobId].exists, "Job not found");
        return milestones[jobId][step];
    }
}
