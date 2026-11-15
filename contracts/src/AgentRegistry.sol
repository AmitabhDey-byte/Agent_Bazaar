// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

contract AgentRegistry is Ownable {
    struct Agent {
        address owner;
        address payTo;
        uint128 price;
        uint64 updatedAt;
        bool active;
        string endpoint;
        string capability;
        uint128 successfulWeight;
        uint128 totalWeight;
    }
    uint256 public count;
    uint256 public constant HALF_LIFE = 30 days;
    uint256 public constant PRIOR_WEIGHT = 1_000_000;
    mapping(uint256 => Agent) private agents;
    mapping(address => bool) public reporters;
    mapping(bytes32 => bool) public receipts;
    error Unauthorized();
    error InvalidAgent();
    error DuplicateReceipt();
    event Registered(uint256 indexed id, address indexed owner, string capability, string endpoint);
    event AgentUpdated(uint256 indexed id, uint128 price, bool active);
    event ReputationUpdated(uint256 indexed id, bytes32 indexed receipt, uint128 value, bool success, uint256 score);
    event ReporterUpdated(address indexed reporter, bool allowed);

    constructor(address administrator) Ownable(administrator) {}

    function register(string calldata endpoint, string calldata capability, uint128 price, address payTo) external returns (uint256 id) {
        _validate(endpoint, capability, price, payTo);
        id = ++count;
        agents[id] = Agent(msg.sender, payTo, price, uint64(block.timestamp), true, endpoint, capability, 0, 0);
        emit Registered(id, msg.sender, capability, endpoint);
    }

    function update(uint256 id, string calldata endpoint, uint128 price, address payTo, bool active) external {
        Agent storage a = agents[id];
        if (a.owner != msg.sender) revert Unauthorized();
        _validate(endpoint, a.capability, price, payTo);
        a.endpoint = endpoint;
        a.price = price;
        a.payTo = payTo;
        a.active = active;
        emit AgentUpdated(id, price, active);
    }

    function setReporter(address reporter, bool allowed) external onlyOwner {
        if (reporter == address(0)) revert InvalidAgent();
        reporters[reporter] = allowed;
        emit ReporterUpdated(reporter, allowed);
    }

    function getAgent(uint256 id) external view returns (Agent memory) {
        if (agents[id].owner == address(0)) revert InvalidAgent();
        return agents[id];
    }

    function reputation(uint256 id) public view returns (uint256) {
        Agent storage a = agents[id];
        if (a.owner == address(0)) revert InvalidAgent();
        uint256 periods = (block.timestamp - a.updatedAt) / HALF_LIFE;
        uint256 total = periods >= 128 ? 0 : uint256(a.totalWeight) >> periods;
        uint256 good = periods >= 128 ? 0 : uint256(a.successfulWeight) >> periods;
        return (good * 10_000 + PRIOR_WEIGHT * 5_000) / (total + PRIOR_WEIGHT);
    }

    function recordOutcome(uint256 id, uint128 value, bool success, bytes32 receipt) external {
        if (!reporters[msg.sender]) revert Unauthorized();
        Agent storage a = agents[id];
        if (a.owner == address(0) || value == 0 || receipt == bytes32(0)) revert InvalidAgent();
        if (receipts[receipt]) revert DuplicateReceipt();
        receipts[receipt] = true;
        uint256 periods = (block.timestamp - a.updatedAt) / HALF_LIFE;
        uint128 total = periods >= 128 ? 0 : a.totalWeight >> periods;
        uint128 good = periods >= 128 ? 0 : a.successfulWeight >> periods;
        a.totalWeight = total + value;
        a.successfulWeight = good + (success ? value : 0);
        // Preserve the fractional half-life so frequent reports cannot suppress decay.
        a.updatedAt = uint64(block.timestamp - (block.timestamp - a.updatedAt) % HALF_LIFE);
        emit ReputationUpdated(id, receipt, value, success, reputation(id));
    }

    function _validate(string memory endpoint, string memory capability, uint128 price, address payTo) private pure {
        bytes memory e = bytes(endpoint);
        if (e.length < 9 || e.length > 512 || bytes(capability).length == 0 || bytes(capability).length > 64 || price == 0 || payTo == address(0)) revert InvalidAgent();
        if (keccak256(bytes(_prefix(e))) != keccak256("https://")) revert InvalidAgent();
    }

    function _prefix(bytes memory value) private pure returns (string memory) {
        bytes memory prefix = new bytes(8);
        for (uint256 i; i < 8; ++i) prefix[i] = value[i];
        return string(prefix);
    }
}
