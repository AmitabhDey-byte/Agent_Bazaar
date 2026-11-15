// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;
import {Test} from "forge-std/Test.sol";
import {StdInvariant} from "forge-std/StdInvariant.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {AgentRegistry} from "../src/AgentRegistry.sol";
import {Escrow} from "../src/Escrow.sol";

contract TestUSDC is ERC20 {
    constructor() ERC20("Test fixture USDC", "USDC") {}
    function mint(address to, uint256 amount) external { _mint(to, amount); }
    function decimals() public pure override returns (uint8) { return 6; }
}

contract BazaarTest is Test {
    AgentRegistry registry; Escrow escrow; TestUSDC token;
    uint256 verifierKey = 0xA11CE;
    uint256 agentId;
    address recipient = address(0xBEEF);
    function setUp() public {
        registry = new AgentRegistry(address(this));
        token = new TestUSDC();
        escrow = new Escrow(token, registry, vm.addr(verifierKey));
        registry.setReporter(address(this), true);
        registry.setReporter(address(escrow), true);
        agentId = registry.register("https://agent.example/run", "summarizer", 1000, recipient);
        token.mint(address(this), type(uint128).max);
        token.approve(address(escrow), type(uint256).max);
    }
    function signature(bytes32 id, bytes32 result, uint64 deadline) internal view returns (bytes memory) {
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(verifierKey, escrow.approvalDigest(id, result, deadline));
        return abi.encodePacked(r, s, v);
    }
    function testReleaseAndReplayProtection() public {
        uint64 deadline = uint64(block.timestamp + 1 days);
        bytes32 id = escrow.fund(agentId, 100_000, deadline);
        bytes32 result = keccak256("verified result");
        bytes memory sig = signature(id, result, deadline);
        escrow.release(id, result, deadline, sig);
        assertEq(token.balanceOf(recipient), 100_000);
        assertEq(escrow.totalLocked(), 0);
        assertGt(registry.reputation(agentId), 5000);
        vm.expectRevert(Escrow.InvalidJob.selector);
        escrow.release(id, result, deadline, sig);
    }
    function testCannotRefundEarlyOrByStranger() public {
        uint64 deadline = uint64(block.timestamp + 1 days);
        bytes32 id = escrow.fund(agentId, 100_000, deadline);
        vm.expectRevert(Escrow.InvalidJob.selector); escrow.refund(id);
        vm.warp(deadline);
        vm.prank(recipient); vm.expectRevert(Escrow.Unauthorized.selector); escrow.refund(id);
        uint256 balance = token.balanceOf(address(this)); escrow.refund(id);
        assertEq(token.balanceOf(address(this)), balance + 100_000);
        assertEq(escrow.totalLocked(), 0);
    }
    function testWrongSignatureAndExpiry() public {
        uint64 deadline = uint64(block.timestamp + 1 days);
        bytes32 id = escrow.fund(agentId, 100_000, deadline);
        bytes32 result = keccak256("result");
        bytes memory sig = signature(id, result, deadline);
        vm.expectRevert(Escrow.InvalidSignature.selector); escrow.release(id, keccak256("tampered"), deadline, sig);
        vm.warp(deadline);
        vm.expectRevert(Escrow.InvalidJob.selector); escrow.release(id, result, deadline, sig);
    }
    function testRegistrationAndReporterAccess() public {
        vm.prank(recipient); vm.expectRevert(AgentRegistry.Unauthorized.selector);
        registry.update(agentId, "https://evil.example", 1, recipient, true);
        vm.prank(recipient); vm.expectRevert(AgentRegistry.Unauthorized.selector);
        registry.recordOutcome(agentId, 1, true, keccak256("receipt"));
        vm.expectRevert(AgentRegistry.InvalidAgent.selector); registry.register("http://unsafe", "a", 1, recipient);
    }
    function testPaymentWeightDecayAndDuplicateReceipt() public {
        registry.recordOutcome(agentId, 10_000_000, true, keccak256("one"));
        uint256 score = registry.reputation(agentId);
        registry.recordOutcome(agentId, 1, false, keccak256("two"));
        assertApproxEqAbs(registry.reputation(agentId), score, 1);
        vm.expectRevert(AgentRegistry.DuplicateReceipt.selector);
        registry.recordOutcome(agentId, 1, true, keccak256("one"));
        vm.warp(block.timestamp + 300 days);
        assertLt(registry.reputation(agentId), score);
        vm.warp(block.timestamp + 4000 days);
        assertEq(registry.reputation(agentId), 5000);
    }
    function testFuzzConservation(uint128 raw, bool releaseIt) public {
        uint128 amount = uint128(bound(raw, 1, 1e18));
        uint64 deadline = uint64(block.timestamp + 1 days);
        uint256 beforeBalance = token.balanceOf(address(this)) + token.balanceOf(recipient);
        bytes32 id = escrow.fund(agentId, amount, deadline);
        if (releaseIt) {
            bytes32 result = keccak256("result");
            escrow.release(id, result, deadline, signature(id, result, deadline));
        } else { vm.warp(deadline); escrow.refund(id); }
        assertEq(token.balanceOf(address(this)) + token.balanceOf(recipient), beforeBalance);
        assertEq(token.balanceOf(address(escrow)), 0);
    }
    function testFuzzScoreBounded(uint128 value, bool success) public {
        value = uint128(bound(value, 1, type(uint120).max));
        registry.recordOutcome(agentId, value, success, keccak256(abi.encode(value, success)));
        assertLe(registry.reputation(agentId), 10_000);
    }
}

contract EscrowHandler is Test {
    Escrow public escrow; TestUSDC public token; uint256 public agentId;
    bytes32[] public ids;
    constructor(Escrow e, TestUSDC t, uint256 a) { escrow = e; token = t; agentId = a; token.approve(address(e), type(uint256).max); }
    function deposit(uint96 raw) external {
        uint128 amount = uint128(bound(raw, 1, 1e12));
        token.mint(address(this), amount);
        ids.push(escrow.fund(agentId, amount, uint64(block.timestamp + 1 hours)));
    }
    function refund(uint256 index) external {
        if (ids.length == 0) return;
        bytes32 id = ids[index % ids.length];
        (,,,, uint64 expiry, Escrow.State state) = escrow.jobs(id);
        if (state != Escrow.State.Funded) return;
        vm.warp(expiry > block.timestamp ? expiry : block.timestamp);
        escrow.refund(id);
    }
}
contract EscrowInvariant is StdInvariant, Test {
    Escrow escrow; TestUSDC token;
    function setUp() public {
        AgentRegistry registry = new AgentRegistry(address(this));
        token = new TestUSDC(); escrow = new Escrow(token, registry, address(1));
        uint256 id = registry.register("https://agent.example/run", "summarizer", 1, address(2));
        EscrowHandler handler = new EscrowHandler(escrow, token, id);
        targetContract(address(handler));
    }
    function invariantCollateralCoversEveryOutstandingJob() public view {
        assertEq(token.balanceOf(address(escrow)), escrow.totalLocked());
    }
}
