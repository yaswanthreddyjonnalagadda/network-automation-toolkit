# Network Automation Toolkit

![Python](https://img.shields.io/badge/python-3.9%2B-blue) ![Netmiko](https://img.shields.io/badge/netmiko-4.x-green)

A Python-based network automation toolkit for managing and monitoring a small enterprise Cisco network. Demonstrates device inventory, config backup, interface monitoring, and OSPF neighbor verification.

## Business Scenario

**Organization:** Contoso Logistics (fictional) | **Environment:** Small enterprise campus

The network team manually logs into each device for routine checks. This toolkit automates repetitive tasks using Python and Netmiko.

## Network Topology

| Device | Role | Management IP | Platform |
|--------|------|---------------|----------|
| RTR-01 | Core Router | 192.168.100.1 | Cisco IOS |
| RTR-02 | Distribution Router | 192.168.100.2 | Cisco IOS |
| SW-01 | Access Switch | 192.168.100.11 | Cisco IOS |
| SW-02 | Access Switch | 192.168.100.12 | Cisco IOS |

### VLANs

| VLAN ID | Name | Subnet | Purpose |
|---------|------|--------|---------|
| 10 | CORP-DATA | 10.10.10.0/24 | Corporate workstations |
| 20 | CORP-VOICE | 10.10.20.0/24 | VoIP phones |
| 30 | CORP-MGMT | 192.168.100.0/24 | Management |
| 99 | NATIVE | N/A | Native VLAN |

OSPF: Area 0, Process ID 1, Router IDs via Loopback0. See diagrams/topology-description.md.

## Technologies

| Category | Technology |
|----------|------------|
| Language | Python 3.9+ |
| SSH Automation | Netmiko 4.x |
| Logging | Python logging |
| Network OS | Cisco IOS |
| Routing Protocol | OSPF Area 0 |
| Management | SSH v2 |

## Automation Goals

1. Config Backup - Timestamped running configs
2. Interface Status - Flag down interfaces
3. OSPF Monitor - Verify FULL adjacencies
4. Inventory Collector - Hostname, IOS version, serial, uptime

## Setup

```bash
git clone https://github.com/yourusername/network-automation-toolkit.git
cd network-automation-toolkit
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Create devices.yml (never commit this file):

```yaml
devices:
  - hostname: 192.168.100.1
    device_type: cisco_ios
    username: netadmin
    password: "your_password"
    secret: "your_enable_secret"
    name: RTR-01
  - hostname: 192.168.100.2
    device_type: cisco_ios
    username: netadmin
    password: "your_password"
    secret: "your_enable_secret"
    name: RTR-02
  - hostname: 192.168.100.11
    device_type: cisco_ios
    username: netadmin
    password: "your_password"
    secret: "your_enable_secret"
    name: SW-01
  - hostname: 192.168.100.12
    device_type: cisco_ios
    username: netadmin
    password: "your_password"
    secret: "your_enable_secret"
    name: SW-02
```

## Running Scripts

```bash
python scripts/backup_configs.py
python scripts/interface_checker.py
python scripts/ospf_neighbor_monitor.py
python scripts/inventory_collector.py
```

## Design Decisions

**Netmiko over Paramiko:** Handles Cisco IOS prompts and paging automatically.
**OSPF over EIGRP:** Open standard, vendor-agnostic, broadly applicable.
**SSH over Telnet:** Industry security standard, Telnet disabled on all devices.
**Python logging:** Supports log levels, file output, and future Splunk/ELK integration.

## Future Improvements

| Enhancement | Priority |
|-------------|----------|
| Ansible Integration | Medium |
| Flask Dashboard | Low |
| Email Alerting on OSPF drops | High |
| Scheduled Execution (cron) | High |
| Cisco DNA Center REST API | Low |

## License

MIT License - Portfolio project demonstrating enterprise network automation with Python and Cisco IOS.
