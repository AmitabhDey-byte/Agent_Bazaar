// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {AgentRegistry} from "./AgentRegistry.sol";

contract Escrow is ReentrancyGuard, EIP712 {
    using SafeERC20 for IERC20;
    enum State { None, Funded, Released, Refunded }
    struct Job { address payer; address recipient; uint256 agentId; uint128 amount; uint64 expiresAt; State state; }
    IERC20 public immutable token;
    AgentRegistry public immutable registry;
    address public immutable verifier;
    uint256 public totalLocked;
    mapping(bytes32 => Job) public jobs;
    mapping(address => uint256) public nonces;
    bytes32 public constant APPROVAL_TYPEHASH = keccak256("Approval(bytes32 jobId,bytes32 resultHash,address recipient,uint128 amount,uint64 deadline)");
    error InvalidJob();
    error InvalidSignature();
    error Unauthorized();
    event Funded(bytes32 indexed jobId, uint256 indexed agentId, address indexed payer, address recipient, uint128 amount, uint64 expiresAt);
    event Released(bytes32 indexed jobId, bytes32 resultHash);
    event Refunded(bytes32 indexed jobId);

    constructor(IERC20 usdc, AgentRegistry agentRegistry, address trustedVerifier) EIP712("AgentBazaarEscrow", "1") {
        if (address(usdc) == address(0) || address(agentRegistry) == address(0) || trustedVerifier == address(0)) revert InvalidJob();
        token = usdc; registry = agentRegistry; verifier = trustedVerifier;
    }

    function fund(uint256 agentId, uint128 amount, uint64 expiresAt) external nonReentrant returns (bytes32 id) {
        AgentRegistry.Agent memory a = registry.getAgent(agentId);
        if (!a.active || amount == 0 || expiresAt <= block.timestamp || expiresAt > block.timestamp + 30 days) revert InvalidJob();
        id = keccak256(abi.encode(block.chainid, address(this), msg.sender, nonces[msg.sender]++));
        jobs[id] = Job(msg.sender, a.payTo, agentId, amount, expiresAt, State.Funded);
        totalLocked += amount;
        uint256 beforeBalance = token.balanceOf(address(this));
        token.safeTransferFrom(msg.sender, address(this), amount);
        if (token.balanceOf(address(this)) != beforeBalance + amount) revert InvalidJob();
        emit Funded(id, agentId, msg.sender, a.payTo, amount, expiresAt);
    }

    function approvalDigest(bytes32 id, bytes32 resultHash, uint64 deadline) public view returns (bytes32) {
        Job storage job = jobs[id];
        return _hashTypedDataV4(keccak256(abi.encode(APPROVAL_TYPEHASH, id, resultHash, job.recipient, job.amount, deadline)));
    }

    function release(bytes32 id, bytes32 resultHash, uint64 deadline, bytes calldata signature) external nonReentrant {
        Job storage job = jobs[id];
        if (job.state != State.Funded || block.timestamp >= job.expiresAt || block.timestamp > deadline || resultHash == bytes32(0)) revert InvalidJob();
        if (ECDSA.recover(approvalDigest(id, resultHash, deadline), signature) != verifier) revert InvalidSignature();
        job.state = State.Released;
        totalLocked -= job.amount;
        token.safeTransfer(job.recipient, job.amount);
        registry.recordOutcome(job.agentId, job.amount, true, keccak256(abi.encode(address(this), id)));
        emit Released(id, resultHash);
    }

    function refund(bytes32 id) external nonReentrant {
        Job storage job = jobs[id];
        if (msg.sender != job.payer) revert Unauthorized();
        if (job.state != State.Funded || block.timestamp < job.expiresAt) revert InvalidJob();
        job.state = State.Refunded;
        totalLocked -= job.amount;
        token.safeTransfer(job.payer, job.amount);
        emit Refunded(id);
    }
}
