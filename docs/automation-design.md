# Automation Design Document
## Network Automation Toolkit - Contoso Logistics

---

## Overview

This document explains the technical design decisions behind the Network Automation Toolkit, including tool selection, script architecture, and operational philosophy.

---

## Tool Selection

### Why Netmiko?

Netmiko was chosen as the primary SSH library for the following reasons:

**Cisco IOS-specific handling:** Raw Paramiko requires manual handling of Cisco quirks — terminal length, enable mode prompts, pager output, and banner prompts. Netmiko abstracts all of this behind a clean API.

**Device type abstraction:** By specifying `device_type: cisco_ios`, Netmiko automatically adjusts its behavior for Cisco IOS syntax. If the environment ever expands to Arista or Juniper, only the device_type field changes.

**Community and maintenance:** Netmiko is actively maintained and widely used in the network automation community, reducing the risk of deprecation.

**Paramiko as a fallback:** Paramiko is still listed in requirements.txt because Netmiko depends on it. Direct Paramiko use would only be needed for non-standard SSH scenarios not covered by Netmiko.

### Why YAML for Inventory?

YAML provides human-readable device inventory that can be version controlled (without credentials), parsed by both Python and Ansible, and extended with additional device metadata (roles, locations, etc.) without code changes.

### Why Python logging over print()?

The `logging` module provides:
- Log level control (DEBUG/INFO/WARNING/ERROR)
- Simultaneous console and file output
- Standardized log format with timestamps
- Easy integration with Splunk, ELK, or CloudWatch in the future

---

## Script Architecture

### Design Principles

**Single Responsibility:** Each script has one job. `backup_configs.py` only does backups. `ospf_neighbor_monitor.py` only checks OSPF. This makes each script easier to understand, test, and modify independently.

**Fail Gracefully:** Every script uses try/except blocks with specific exception types. A single device failure should never crash the entire run. Errors are logged and the script continues to the next device.

**No Hard-coded Credentials:** All credentials live in `devices.yml`, which is excluded from git via `.gitignore`. This follows the principle of separating configuration from code.

**Sequential Execution:** Scripts connect to devices one at a time (not concurrently). This is intentional for a small 4-device fleet: it's simpler, produces cleaner logs, and avoids overwhelming devices with simultaneous SSH connections. For larger fleets (50+ devices), concurrent execution using `concurrent.futures.ThreadPoolExecutor` would be the next step.

### Common Patterns

All scripts share the same structure:

1. **Setup logging** — consistent format across all scripts
2. **Load inventory** — `load_inventory()` function reads `devices.yml`
3. **Per-device function** — isolated connection logic with exception handling
4. **Main loop** — iterates over all devices, collects results
5. **Summary report** — aggregated output at the end

This consistent pattern reduces cognitive load when switching between scripts.

---

## Network Design Decisions

### OSPF over Static Routing

OSPF was chosen over static routing for the following reasons:

- **Automatic convergence:** If the P2P link between RTR-01 and RTR-02 fails, OSPF would automatically detect the failure and remove unreachable routes (if redundant paths existed).
- **Scalability:** Adding new routers or subnets only requires adding them to OSPF — no manual static route updates on every router.
- **Industry relevance:** OSPF is the dominant IGP in enterprise networks, making this topology broadly applicable as a portfolio project.

### Single Area 0

All OSPF-enabled interfaces are in Area 0 (the backbone area). A multi-area design would be appropriate when the network grows beyond 50+ routers, where LSA flooding becomes a performance concern. For this small topology, a single area keeps the design simple without sacrificing correctness.

### Loopback Interfaces as Router IDs

OSPF router IDs are assigned via Loopback0 interfaces rather than relying on automatic selection. This provides:

- **Stability:** Loopbacks never go down, preventing router ID changes and unnecessary OSPF reconvergence.
- **Identification:** The router ID directly maps to the device (RTR-01 = 1.1.1.1, RTR-02 = 2.2.2.2), simplifying troubleshooting.

### /30 Subnets for P2P Links

The link between RTR-01 and RTR-02 uses a /30 subnet (10.0.1.0/30), providing exactly 2 usable IP addresses. This conserves address space and clearly communicates the point-to-point nature of the link.

### SSH v2 Only

All device configurations disable Telnet (`transport input ssh`) and require SSH v2. Telnet transmits credentials in plaintext and has no place in a modern network environment.

---

## Operational Considerations

### Credential Management

For this lab environment, credentials are stored in `devices.yml`. In a production environment, consider:

- **HashiCorp Vault** — secrets as a service with audit logging
- **CyberArk** — enterprise PAM (Privileged Access Management)
- **Environment variables** — simple approach for CI/CD pipelines
- **Ansible Vault** — if migrating to Ansible playbooks

### Network Access Controls

Automation scripts should connect from a dedicated management workstation or jump host on the management VLAN (192.168.100.0/24). VTY lines on all devices use `transport input ssh` and `login authentication default` to enforce SSH-only access with centralized authentication.

### Rate Limiting Awareness

Cisco IOS devices have default limits on concurrent VTY sessions (typically 5-15 lines). For larger environments, be mindful of session limits when running concurrent automation.

### Backup Retention

Each backup run creates a timestamped directory (`configs/backups/YYYYMMDD_HHMMSS/`). A retention policy should be implemented in production — for example, keep the last 30 days of backups and archive older ones to object storage (S3, Azure Blob).

---

## Scalability Path

This toolkit is intentionally sized for a small network. As the environment grows:

| Scale | Recommended Change |
|-------|-------------------|
| 10-50 devices | Add concurrent execution with ThreadPoolExecutor |
| 50+ devices | Migrate to Ansible for idempotent, declarative automation |
| 100+ devices | Integrate with Cisco DNA Center or NSO for model-driven automation |
| Any size | Add a database backend (SQLite/PostgreSQL) for inventory and change tracking |
