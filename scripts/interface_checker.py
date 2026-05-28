#!/usr/bin/env python3
"""
interface_checker.py - Interface Status Monitor
Network Automation Toolkit

Description:
    Connects to each device and retrieves 'show ip interface brief'.
    Flags any interfaces that are administratively down or show
    line-protocol as down (potential connectivity issue).

Usage:
    python scripts/interface_checker.py
"""

import os
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
        logging.FileHandler(f"{LOG_DIR}/interface_check.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)


def load_inventory(inventory_file: str) -> list:
    """Load device inventory from YAML file."""
    if not os.path.exists(inventory_file):
        raise FileNotFoundError(f"Inventory file not found: {inventory_file}")

    with open(inventory_file, "r") as f:
        data = yaml.safe_load(f)

    return data.get("devices", [])


def parse_interface_brief(output: str) -> list:
    """
    Parse 'show ip interface brief' output into a list of interface dictionaries.

    Cisco IOS output format:
        Interface      IP-Address      OK? Method Status                Protocol
        GigabitEthernet0/0  10.0.0.1  YES NVRAM  up                    up
        GigabitEthernet0/1  unassigned YES unset  administratively down down

    Args:
        output: Raw command output string

    Returns:
        List of dicts with keys: interface, ip, status, protocol
    """
    interfaces = []
    lines = output.strip().split("\n")

    for line in lines:
        # Skip the header line
        if "Interface" in line and "Status" in line:
            continue

        parts = line.split()
        if len(parts) >= 5:
            interfaces.append({
                "interface": parts[0],
                "ip": parts[1],
                # Status and protocol may be multi-word (e.g. "administratively down")
                # Join remaining parts and split on known delimiters
                "status": " ".join(parts[3:-1]) if len(parts) > 5 else parts[3],
                "protocol": parts[-1],
            })

    return interfaces


def check_device_interfaces(device: dict) -> dict:
    """
    Retrieve and analyze interface status for a single device.

    Args:
        device: Netmiko connection parameters dict plus 'name' key

    Returns:
        Dict with device name, interfaces list, and any issues found
    """
    device_name = device.get("name", device.get("hostname", "unknown"))
    connection_params = {k: v for k, v in device.items() if k != "name"}
    result = {"device": device_name, "interfaces": [], "issues": [], "error": None}

    logger.info(f"Checking interfaces on {device_name} ({device.get('hostname')})...")

    try:
        with ConnectHandler(**connection_params) as net_connect:
            if not net_connect.check_enable_mode():
                net_connect.enable()

            output = net_connect.send_command("show ip interface brief")
            interfaces = parse_interface_brief(output)
            result["interfaces"] = interfaces

            # Flag interfaces with issues
            for intf in interfaces:
                status = intf.get("status", "").lower()
                protocol = intf.get("protocol", "").lower()

                if "administratively down" in status:
                    # Admin down is intentional - log as INFO, not WARNING
                    logger.info(
                        f"  [{device_name}] {intf['interface']} - ADMIN DOWN (intentional shutdown)"
                    )

                elif status == "down" or protocol == "down":
                    # Line protocol down indicates a physical or layer-2 problem
                    issue = f"{intf['interface']} is DOWN (status={intf['status']}, protocol={protocol})"
                    result["issues"].append(issue)
                    logger.warning(f"  [{device_name}] ISSUE: {issue}")

                else:
                    logger.info(
                        f"  [{device_name}] {intf['interface']} - UP/UP ({intf['ip']})"
                    )

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
    """Main entry point for the interface checker."""
    logger.info("=" * 60)
    logger.info("Network Automation Toolkit - Interface Status Check")
    logger.info("=" * 60)

    try:
        devices = load_inventory("devices.yml")
    except FileNotFoundError as e:
        logger.error(str(e))
        return

    all_results = []
    total_issues = 0

    for device in devices:
        result = check_device_interfaces(device)
        all_results.append(result)
        total_issues += len(result.get("issues", []))

    # Summary
    logger.info("=" * 60)
    logger.info("INTERFACE CHECK SUMMARY")
    logger.info("=" * 60)

    for r in all_results:
        device = r["device"]
        issues = r.get("issues", [])
        error = r.get("error")

        if error:
            logger.error(f"  {device}: FAILED ({error})")
        elif issues:
            logger.warning(f"  {device}: {len(issues)} issue(s) found")
            for issue in issues:
                logger.warning(f"    - {issue}")
        else:
            logger.info(f"  {device}: All interfaces OK")

    logger.info("-" * 60)
    if total_issues > 0:
        logger.warning(f"Total issues found: {total_issues} - Review warnings above")
    else:
        logger.info("No interface issues detected across all devices.")


if __name__ == "__main__":
    main()
