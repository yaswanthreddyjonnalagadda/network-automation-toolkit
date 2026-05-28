# Network Topology Description
## Contoso Logistics - Network Automation Toolkit Lab

This document describes the network topology for the draw.io diagram. Use it as a reference when building or recreating the visual topology diagram.

---

## Logical Topology Overview

```
                    [Internet/MPLS]
                          |
                    Gi0/0 (10.0.0.1/30)
                          |
                     +----------+
                     |  RTR-01  |  Core Router
                     | 1.1.1.1  |  192.168.100.1 (Mgmt)
                     +----------+
                          |
                    Gi0/1 <──── OSPF Area 0 ────> Gi0/0
              (10.0.1.1/30)                   (10.0.1.2/30)
                          |                         |
                     +----------+           +----------+
                     |  RTR-01  |           |  RTR-02  |  Distribution
                     | VLAN 10  |           | 2.2.2.2  |  192.168.100.2
                     +----------+           +----------+
                          |                         |
                    Gi0/2 (10.10.10.1/24)     Gi0/1 (10.10.20.1/24)
                          |                         |
                   [VLAN 10 Trunk]           [VLAN 20 Trunk]
                          |                         |
                     +----------+           +----------+
                     |  SW-01   |           |  SW-02   |  Access Switches
                     |192.168   |           |192.168   |
                     |100.11    |           |100.12    |
                     +----------+           +----------+
                     /    |    \             /    |    \
                 Access  Access  Trunk  Access  Access  Trunk
                (Gi1/0/1-24) (Gi1/0/25-40)    (Gi1/0/1-24)
                VLAN 10  VLAN 20/Voice     VLAN 10  VLAN 20/Voice
```

---

## draw.io Diagram Instructions

### Step 1: Create the Canvas
Open draw.io and create a new blank diagram. Set the page to landscape orientation.

### Step 2: Add Devices (use Network shapes library)

| Shape | Label | Icon Suggestion |
|-------|-------|-----------------|
| Router | RTR-01 | Network > Router (Cisco style) |
| Router | RTR-02 | Network > Router (Cisco style) |
| Switch | SW-01 | Network > Switch (L2) |
| Switch | SW-02 | Network > Switch (L2) |
| Cloud | Internet/MPLS | General > Cloud |

### Step 3: Layout

Place devices in this vertical arrangement:
- **Top:** Internet/MPLS cloud
- **Level 2:** RTR-01 (left-center)
- **Level 3:** RTR-02 (right of RTR-01, same level)
- **Level 4:** SW-01 (below RTR-01) and SW-02 (below RTR-02)

### Step 4: Add Connections and Labels

**Connection 1:** Internet cloud → RTR-01 Gi0/0
- Label: WAN Uplink | 10.0.0.1/30

**Connection 2:** RTR-01 Gi0/1 ←→ RTR-02 Gi0/0
- Label: P2P OSPF Link | 10.0.1.0/30
- Add OSPF lightning bolt symbol or annotation: "OSPF Area 0"

**Connection 3:** RTR-01 Gi0/2 ↓ SW-01 Gi1/0/48
- Label: Trunk | VLAN 10,20,30 | Native VLAN 99

**Connection 4:** RTR-02 Gi0/1 ↓ SW-02 Gi1/0/48
- Label: Trunk | VLAN 10,20,30 | Native VLAN 99

### Step 5: Add VLAN Annotations

Add colored rectangles (semi-transparent fill) as legend:
- **Blue:** VLAN 10 CORP-DATA (10.10.10.0/24)
- **Green:** VLAN 20 CORP-VOICE (10.10.20.0/24)
- **Orange:** VLAN 30 CORP-MGMT (192.168.100.0/24)

### Step 6: Add IP Addressing Table

Use a table shape or text box listing all interface IPs:

| Device | Interface | IP Address | VLAN/Network |
|--------|-----------|------------|--------------|
| RTR-01 | Gi0/0 | 10.0.0.1/30 | WAN |
| RTR-01 | Gi0/1 | 10.0.1.1/30 | P2P to RTR-02 |
| RTR-01 | Gi0/2 | 10.10.10.1/24 | VLAN 10 |
| RTR-01 | Gi0/3 | 192.168.100.1/24 | MGMT |
| RTR-01 | Lo0 | 1.1.1.1/32 | OSPF RID |
| RTR-02 | Gi0/0 | 10.0.1.2/30 | P2P to RTR-01 |
| RTR-02 | Gi0/1 | 10.10.20.1/24 | VLAN 20 |
| RTR-02 | Gi0/2 | 192.168.100.2/24 | MGMT |
| RTR-02 | Lo0 | 2.2.2.2/32 | OSPF RID |
| SW-01 | Vlan30 | 192.168.100.11/24 | MGMT |
| SW-02 | Vlan30 | 192.168.100.12/24 | MGMT |

### Step 7: Add Legend

Bottom-right corner legend:
- Solid line = Layer 3 routed link
- Dashed line = Trunk (Layer 2)
- Lightning bolt = OSPF Area 0
- Loopback symbol = Router ID

---

## OSPF Adjacency Summary

```
RTR-01 (1.1.1.1)  <──── OSPF FULL ────>  RTR-02 (2.2.2.2)
         \___________Area 0___________/

Expected OSPF neighbors:
  RTR-01: 2.2.2.2 (RTR-02) via Gi0/1 - FULL
  RTR-02: 1.1.1.1 (RTR-01) via Gi0/0 - FULL
```

---

## Management Subnet

All 4 devices are reachable on the management subnet 192.168.100.0/24.

Automation scripts connect to these IPs via SSH from the management workstation (assumed to be on the same subnet or routed to it).

| Device | Management IP | Default Gateway |
|--------|--------------|-----------------|
| RTR-01 | 192.168.100.1 | N/A (is the gateway) |
| RTR-02 | 192.168.100.2 | 192.168.100.1 |
| SW-01 | 192.168.100.11 | 192.168.100.1 |
| SW-02 | 192.168.100.12 | 192.168.100.2 |
