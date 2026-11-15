// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;
import {Script} from "forge-std/Script.sol";
import {AgentRegistry} from "../src/AgentRegistry.sol";
import {Escrow} from "../src/Escrow.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract Deploy is Script {
    function run() external returns (AgentRegistry registry, Escrow escrow) {
        require(block.chainid == 84532, "Base Sepolia only");
        uint256 key = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address admin = vm.addr(key);
        vm.startBroadcast(key);
        registry = new AgentRegistry(admin);
        escrow = new Escrow(IERC20(vm.envAddress("USDC_ADDRESS")), registry, vm.envAddress("VERIFIER_ADDRESS"));
        registry.setReporter(address(escrow), true);
        registry.setReporter(vm.envAddress("ORCHESTRATOR_ADDRESS"), true);
        vm.stopBroadcast();
    }
}
