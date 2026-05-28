#!/usr/bin/env python3
"""
backup_configs.py - Configuration Backup Script
Network Automation Toolkit

Connects to each device via SSH and saves a timestamped copy of the
running configuration to the local filesystem.

Usage:
    python scripts/backup_configs.py
"""

import os
import logging
import yaml
from datetime import datetime
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

# ─────────────────────────────────────────────
# LOGGING SETUP
# Using logging module instead of print() allows log level control,
# file output, and future integration with Splunk/ELK.
# ─────────────────────────────────────────────
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"{LOG_DIR}/backup.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)


def load_inventory(inventory_file: str) -> list:
    """
    Load device inventory from a YAML file.

    Credentials are kept out of the script and in the YAML file,
    which is excluded from version control via .gitignore.

    Args:
        inventory_file: Path to the YAML inventory file

    Returns:
        List of device dictionaries
    """
    if not os.path.exists(inventory_file):
        raise FileNotFoundError(
            f"Inventory file not found: {inventory_file}\n"
            "Create devices.yml from the README template before running."
        )

    with open(inventory_file, "r") as f:
        data = yaml.safe_load(f)

    devices = data.get("devices", [])
    logger.info(f"Loaded {len(devices)} device(s) from {inventory_file}")
    return devices


def backup_device(device: dict, backup_dir: str) -> bool:
    """
    Connect to a single device and save its running configuration.

    Args:
        device: Dictionary with Netmiko connection params plus 'name' key
        backup_dir: Directory path to save the backup file

    Returns:
        True if backup succeeded, False if it failed
    """
    device_name = device.get("name", device.get("hostname", "unknown"))

    # Build Netmiko connection parameters (exclude custom 'name' key)
    connection_params = {k: v for k, v in device.items() if k != "name"}

    logger.info(f"Connecting to {device_name} ({device.get('hostname')})...")

    try:
        with ConnectHandler(**connection_params) as net_connect:
            logger.info(f"  [{device_name}] Connected successfully")

            # Enter enable mode to access full running config
            if not net_connect.check_enable_mode():
                net_connect.enable()

            # Retrieve running configuration
            # Note: 'show running-config' returns config in memory.
            # If changes were made without 'write memory', startup config differs.
            output = net_connect.send_command("show running-config")

            # Save backup: configs/backups/20240315_092211/RTR-01.cfg
            filename = os.path.join(backup_dir, f"{device_name}.cfg")
            with open(filename, "w") as f:
                f.write(output)

            logger.info(f"  [{device_name}] Backup saved: {filename} ({len(output)} bytes)")
            return True

    except NetmikoTimeoutException:
        logger.error(f"  [{device_name}] TIMEOUT - Device unreachable or SSH blocked")
        return False

    except NetmikoAuthenticationException:
        logger.error(f"  [{device_name}] AUTH FAILED - Check username/password/enable secret")
        return False

    except Exception as e:
        logger.error(f"  [{device_name}] UNEXPECTED ERROR: {str(e)}")
        return False


def main():
    """Main entry point for the backup script."""
    logger.info("=" * 60)
    logger.info("Network Automation Toolkit - Configuration Backup")
    logger.info("=" * 60)

    # Create timestamped backup directory to preserve history
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join("configs", "backups", timestamp)
    os.makedirs(backup_dir, exist_ok=True)
    logger.info(f"Backup directory: {backup_dir}")

    try:
        devices = load_inventory("devices.yml")
    except FileNotFoundError as e:
        logger.error(str(e))
        return

    # Sequential execution is intentional for a small fleet:
    # simpler, safer, and avoids overwhelming devices with concurrent connections
    results = {"success": [], "failed": []}

    for device in devices:
        device_name = device.get("name", device.get("hostname"))
        success = backup_device(device, backup_dir)

        if success:
            results["success"].append(device_name)
        else:
            results["failed"].append(device_name)

    # Summary
    logger.info("=" * 60)
    logger.info(f"Backup complete: {len(results['success'])} succeeded, {len(results['failed'])} failed")

    if results["success"]:
        logger.info(f"  Successful: {', '.join(results['success'])}")

    if results["failed"]:
        logger.warning(f"  Failed:     {', '.join(results['failed'])}")

    logger.info(f"Backup files stored in: {backup_dir}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
