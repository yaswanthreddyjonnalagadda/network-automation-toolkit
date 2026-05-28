#!/usr/bin/env python3
"""
inventory_collector.py - Device Inventory Collector
Network Automation Toolkit

Description:
    Connects to each device and collects:
    - Hostname
    - IOS version
    - Serial number (from 'show version')
    - System uptime
    - Hardware model

    Saves the results to outputs/inventory_report.txt for documentation
    and asset management purposes.

Usage:
    python scripts/inventory_collector.py
"""

import os
import re
import logging
import yaml
from datetime import datetime
from tabulate import tabulate
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

LOG_DIR = "logs"
OUTPUT_DIR = "outputs"
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"{LOG_DIR}/inventory.log", mode="a"),
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


def parse_show_version(output: str) -> dict:
    """
    Extract key system information from 'show version' output.

    We use regex patterns to extract specific fields because IOS version
    output format varies between platforms and IOS releases.

    Args:
        output: Raw 'show version' output

    Returns:
        Dict with ios_version, serial_number, uptime, hardware_model
    """
    info = {
        "ios_version": "unknown",
        "serial_number": "unknown",
        "uptime": "unknown",
        "hardware_model": "unknown",
    }

    # IOS Version - e.g. "Cisco IOS Software, Version 15.7(3)M5"
    version_match = re.search(r"Version\s+([\w().]+)", output)
    if version_match:
        info["ios_version"] = version_match.group(1)

    # Serial Number - e.g. "Processor board ID FTX1234A0BC"
    # Some platforms show serial differently (e.g. switches use 'System serial number')
    serial_match = re.search(
        r"(?:Processor board ID|System serial number)\s+(\S+)", output
    )
    if serial_match:
        info["serial_number"] = serial_match.group(1)

    # Uptime - e.g. "RTR-01 uptime is 47 days, 3 hours, 22 minutes"
    uptime_match = re.search(r"uptime is (.+)", output)
    if uptime_match:
        info["uptime"] = uptime_match.group(1).strip()

    # Hardware model - e.g. "Cisco CISCO2911/K9" or "cisco WS-C2960X-48FPD-L"
    model_match = re.search(r"cisco\s+(\S+)", output, re.IGNORECASE)
    if model_match:
        info["hardware_model"] = model_match.group(1)

    return info


def collect_device_inventory(device: dict) -> dict:
    """
    Connect to a device and collect inventory information.

    Args:
        device: Netmiko connection parameters plus 'name' key

    Returns:
        Dict with hostname, management IP, and parsed inventory data
    """
    device_name = device.get("name", device.get("hostname", "unknown"))
    hostname = device.get("hostname", "unknown")
    connection_params = {k: v for k, v in device.items() if k != "name"}

    result = {
        "name": device_name,
        "management_ip": hostname,
        "ios_version": "ERROR",
        "serial_number": "ERROR",
        "uptime": "ERROR",
        "hardware_model": "ERROR",
        "error": None,
    }

    logger.info(f"Collecting inventory from {device_name} ({hostname})...")

    try:
        with ConnectHandler(**connection_params) as net_connect:
            if not net_connect.check_enable_mode():
                net_connect.enable()

            # 'show version' contains: OS version, uptime, serial number, hardware model
            # Single command gives us everything we need - efficient for a small fleet
            output = net_connect.send_command("show version")
            parsed = parse_show_version(output)

            result.update(parsed)
            logger.info(
                f"  [{device_name}] IOS: {parsed['ios_version']} | "
                f"Serial: {parsed['serial_number']} | "
                f"Uptime: {parsed['uptime']}"
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


def save_report(inventory: list, output_file: str) -> None:
    """
    Save inventory report to a text file using tabulate for formatting.

    Args:
        inventory: List of device inventory dicts
        output_file: Path to save the report
    """
    headers = ["Device", "Management IP", "IOS Version", "Serial Number", "Hardware Model", "Uptime"]
    rows = []

    for device in inventory:
        rows.append([
            device.get("name", ""),
            device.get("management_ip", ""),
            device.get("ios_version", ""),
            device.get("serial_number", ""),
            device.get("hardware_model", ""),
            device.get("uptime", ""),
        ])

    table = tabulate(rows, headers=headers, tablefmt="grid")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_content = f"Network Automation Toolkit - Device Inventory\nGenerated: {timestamp}\n\n{table}\n"

    with open(output_file, "w") as f:
        f.write(report_content)

    logger.info(f"Inventory report saved to: {output_file}")


def main():
    """Main entry point for inventory collection."""
    logger.info("=" * 60)
    logger.info("Network Automation Toolkit - Inventory Collector")
    logger.info("=" * 60)

    try:
        devices = load_inventory("devices.yml")
    except FileNotFoundError as e:
        logger.error(str(e))
        return

    inventory = []

    for device in devices:
        result = collect_device_inventory(device)
        inventory.append(result)

    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"inventory_report_{timestamp}.txt")
    save_report(inventory, output_file)

    # Summary
    logger.info("=" * 60)
    success = sum(1 for d in inventory if not d.get("error"))
    failed = sum(1 for d in inventory if d.get("error"))
    logger.info(f"Inventory complete: {success} collected, {failed} failed")
    logger.info(f"Report saved to: {output_file}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
