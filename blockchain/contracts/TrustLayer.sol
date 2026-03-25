// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract TrustLayer {

    address public owner;

    mapping(address => uint256) public trustScore;
    mapping(address => bool) public blacklisted;
    mapping(uint256 => mapping(address => bytes32)) public updateHashes;

    uint256 public constant INITIAL_TRUST = 100;
    uint256 public constant PENALTY = 20;
    uint256 public constant THRESHOLD = 40;

    event ClientRegistered(address client);
    event HashSubmitted(address client, uint256 round, bytes32 hash);
    event TrustUpdated(address client, uint256 newTrust);
    event Blacklisted(address client);

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized");
        _;
    }

    function registerClient() public {
        require(trustScore[msg.sender] == 0, "Already registered");
        trustScore[msg.sender] = INITIAL_TRUST;
        emit ClientRegistered(msg.sender);
    }

    function submitHash(uint256 round, bytes32 hash) public {
        require(trustScore[msg.sender] > 0, "Not registered");
        require(!blacklisted[msg.sender], "Client blacklisted");
        require(updateHashes[round][msg.sender] == bytes32(0), "Hash already submitted");

        updateHashes[round][msg.sender] = hash;
        emit HashSubmitted(msg.sender, round, hash);
    }

    function penalizeClient(address client) public onlyOwner {
        require(trustScore[client] > 0, "Client not registered");

        if (trustScore[client] >= PENALTY) {
            trustScore[client] -= PENALTY;
        } else {
            trustScore[client] = 0;
        }

        emit TrustUpdated(client, trustScore[client]);

        if (trustScore[client] < THRESHOLD) {
            blacklisted[client] = true;
            emit Blacklisted(client);
        }
    }

    function getTrust(address client) public view returns (uint256) {
        return trustScore[client];
    }
}