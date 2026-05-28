#!/usr/bin/env python3
"""
ospf_neighbor_monitor.py - OSPF Neighbor Adjacency Monitor
Network Automation Toolkit

Description:
    Connects to each router and verifies OSPF neighbor adjacencies.
    Alerts if expected neighbors are not in FULL state, which would
    indicate a routing protocol failure requiring investigation.

    Expected OSPF state for a healthy adjacency: FULL
    States that indicate issues: INIT, 2WAY, EXSTART, EXCHANGE, LOADING

Usage:
    python scripts/ospf_neighbor_monitor.py
"""

import os
import re
import logging
import yaml
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"{LOG_DIR}/ospf_monitor.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)

# Only check routers - switches won't run OSPF in this topology
ROUTER_TYPES = ["core_router", "distribution_router", "router"]


def load_inventory(inventory_file: str) -> list:
    """Load device inventory from YAML file."""
    if not os.path.exists(inventory_file):
        raise FileNotFoundError(f"Inventory file not found: {inventory_file}")

    with open(inventory_file, "r") as f:
        data = yaml.safe_load(f)

    return data.get("devices", [])


def parse_ospf_neighbors(output: str) -> list:
    """
    Parse 'show ip ospf neighbor' output into a list of neighbor dictionaries.

    Sample Cisco IOS output:
        Neighbor ID     Pri   State           Dead Time   Address         Interface
        2.2.2.2           1   FULL/DR         00:00:31    10.0.1.2        GigabitEthernet0/1
        1.1.1.1           1   FULL/BDR        00:00:38    10.0.1.1        GigabitEthernet0/0

    Args:
        output: Raw command output from 'show ip ospf neighbor'

    Returns:
        List of neighbor dicts with keys: neighbor_id, priority, state, address, interface
    """
    neighbors = []

    # Regex pattern matches each neighbor line
    # State field may include DR/BDR role: e.g. "FULL/DR" or "FULL/  -"
    pattern = re.compile(
        r"(\d+\.\d+\.\d+\.\d+)\s+(\d+)\s+(\S+)\s+\S+\s+(\d+\.\d+\.\d+\.\d+)\s+(\S+)"
    )

    for line in output.split("\n"):
        match = pattern.search(line)
        if match:
            neighbor_id, priority, state, address, interface = match.groups()
            neighbors.append({
                "neighbor_id": neighbor_id,
                "priority": int(priority),
                "state": state,  # e.g. "FULL/DR", "FULL/BDR", "INIT"
                "address": address,
                "interface": interface,
            })

    return neighbors


def check_ospf_neighbors(device: dict) -> dict:
    """
    Retrieve and evaluate OSPF neighbor state for a single device.

    A healthy OSPF neighbor shows state starting with 'FULL'.
    Any other state may indicate a problem (MTU mismatch, hello timer
    mismatch, authentication failure, network type mismatch, etc.)

    Args:
        device: Netmiko connection dict plus 'name' key

    Returns:
        Dict with device name, neighbors list, and any issues
    """
    device_name = device.get("name", device.get("hostname", "unknown"))
    connection_params = {k: v for k, v in device.items() if k != "name"}
    result = {"device": device_name, "neighbors": [], "issues": [], "error": None}

    logger.info(f"Checking OSPF neighbors on {device_name} ({device.get('hostname')})...")

    try:
        with ConnectHandler(**connection_params) as net_connect:
            if not net_connect.check_enable_mode():
                net_connect.enable()

            output = net_connect.send_command("show ip ospf neighbor")
            neighbors = parse_ospf_neighbors(output)
            result["neighbors"] = neighbors

            if not neighbors:
                # No neighbors could mean OSPF is not configured, or all neighbors are down
                issue = "No OSPF neighbors found - OSPF may not be configured or all neighbors are down"
                result["issues"].append(issue)
                logger.warning(f"  [{device_name}] WARNING: {issue}")
                return result

            for neighbor in neighbors:
                state = neighbor["state"]
                neighbor_id = neighbor["neighbor_id"]

                if state.startswith("FULL"):
                    # FULL state is healthy - adjacency is established
                    logger.info(
                        f"  [{device_name}] Neighbor {neighbor_id} via {neighbor['interface']} "
                        f"- State: {state} - OK"
                    )
                else:
                    # Non-FULL state indicates an adjacency problem
                    # Common causes:
                    #   INIT: Only one-way hello packets - check ACLs or interface config
                    #   EXSTART/EXCHANGE: MTU mismatch between neighbors
                    #   LOADING: Database exchange incomplete (usually transient)
                    #   2WAY: Normal for non-DR/BDR routers on broadcast segments
                    issue = (
                        f"Neighbor {neighbor_id} via {neighbor['interface']} "
                        f"is in state {state} - expected FULL"
                    )
                    result["issues"].append(issue)
                    logger.warning(f"  [{device_name}] ISSUE: {issue}")

    except NetmikoTimeoutException:
        result["error"] = "TIMEOUT"
        logger.error(f"  [{device_name}] TIMEOUT - Device unreachable")

    except NetmikoAuthenticationException:
        result["error"] = "AUTH_FAILED"
        logger.error(f"  [{device_name}] AUTH FAILED")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"  [{device_name}] ERROR: {str(e)}")

    return result


def main():
    """Main entry point for OSPF neighbor monitoring."""
    logger.info("=" * 60)
    logger.info("Network Automation Toolkit - OSPF Neighbor Monitor")
    logger.info("=" * 60)

    try:
        devices = load_inventory("devices.yml")
    except FileNotFoundError as e:
        logger.error(str(e))
        return

    # Filter to routers only - switches don't participate in OSPF
    # In devices.yml you can optionally add a 'role' field to filter here
    # For now we check all devices and let OSPF output be empty for switches
    all_results = []
    total_issues = 0

    for device in devices:
        result = check_ospf_neighbors(device)
        all_results.append(result)
        total_issues += len(result.get("issues", []))

    # Summary report
    logger.info("=" * 60)
    logger.info("OSPF NEIGHBOR SUMMARY")
    logger.info("=" * 60)

    for r in all_results:
        device = r["device"]
        neighbors = r.get("neighbors", [])
        issues = r.get("issues", [])
        error = r.get("error")

        if error:
            logger.error(f"  {device}: FAILED TO CHECK ({error})")
        elif issues:
            logger.warning(f"  {device}: {len(issues)} issue(s)")
            for issue in issues:
                logger.warning(f"    - {issue}")
        elif not neighbors:
            logger.info(f"  {device}: No OSPF neighbors (may be a switch)")
        else:
            logger.info(f"  {device}: {len(neighbors)} neighbor(s) - ALL FULL")

    logger.info("-" * 60)
    if total_issues > 0:
        logger.warning(f"OSPF issues detected: {total_issues} - Investigate immediately")
        logger.warning("See docs/troubleshooting-guide.md for common OSPF issues")
    else:
        logger.info("OSPF health check PASSED - All adjacencies in FULL state")


if __name__ == "__main__":
    main()
