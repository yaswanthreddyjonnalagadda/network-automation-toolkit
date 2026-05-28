# Troubleshooting Guide
## Network Automation Toolkit - Contoso Logistics

---

## Section 1: SSH Connectivity Issues

### Problem: NetmikoTimeoutException

**Symptom:** Script reports `[DEVICE] TIMEOUT - Device unreachable or SSH blocked`

**Possible Causes and Fixes:**

1. **Device is unreachable at the network level**
   - Verify you can ping the management IP: `ping 192.168.100.1`
   - Check that the management VLAN interface (Vlan30) is up on switches

2. **SSH is not enabled on the device**
   - Log in via console and verify SSH is configured:
     ```
     show ip ssh
     show run | include ssh
     ```
   - If not configured, apply the SSH setup commands from README

3. **Firewall or ACL blocking SSH (port 22)**
   - Check for access-lists applied to VTY lines: `show run | section line vty`
   - Verify the management workstation IP is permitted

4. **Wrong management IP in devices.yml**
   - Double-check the management IP configured on the device: `show ip interface brief`

---

### Problem: NetmikoAuthenticationException

**Symptom:** Script reports `[DEVICE] AUTH FAILED - Check username/password/enable secret`

**Possible Causes and Fixes:**

1. **Wrong username or password in devices.yml**
   - Verify the account exists: `show run | include username`
   - Test manually: `ssh netadmin@192.168.100.1`

2. **Enable secret not set or wrong in devices.yml**
   - If the account has privilege 15, enable mode is not needed
   - Verify privilege level: `show run | include username netadmin`

3. **SSH key mismatch**
   - If the device's RSA keys were regenerated, the known_hosts entry may be stale
   - Remove the stale key: `ssh-keygen -R 192.168.100.1`

4. **Account locked due to repeated failures**
   - Check login failure logs on the device: `show login failures`
   - Wait for lockout period or reset via console

---

## Section 2: OSPF Issues

### Problem: OSPF Neighbors Not Forming (No Output from show ip ospf neighbor)

**Symptom:** ospf_neighbor_monitor.py reports "No OSPF neighbors found"

**Diagnostic Steps:**

```
# On the affected router:
show ip ospf interface
show ip ospf neighbor
debug ip ospf hello   (use carefully - verbose output)
```

**Common Causes:**

1. **OSPF not configured on the interface**
   - Verify the network statement covers the interface subnet
   - Check: `show ip ospf interface GigabitEthernet0/1`

2. **Interface is passive**
   - Passive interfaces don't send OSPF hellos
   - Check: `show ip ospf interface brief` - look for "Passive" status
   - On P2P links between routers, the interface must NOT be passive

3. **Mismatched Hello/Dead timers**
   - Both routers on a link must have the same hello and dead timers
   - Check: `show ip ospf interface Gi0/1` - compare timers on both ends
   - Fix: `ip ospf hello-interval 10` / `ip ospf dead-interval 40`

4. **Mismatched Area IDs**
   - Both ends of the link must be in the same OSPF area
   - Check: `show ip ospf interface` on both routers

---

### Problem: OSPF Neighbor in EXSTART or EXCHANGE State (Not Reaching FULL)

**Symptom:** Neighbor stuck in EXSTART/EXCHANGE state

**Most Common Cause: MTU Mismatch**

OSPF Database Description (DBD) packets include the interface MTU. If the MTU on one end is higher than the other, OSPF will not reach FULL state.

**Diagnosis:**
```
show interface GigabitEthernet0/1
# Check MTU line on both routers
```

**Fix Option 1 - Match MTUs:**
```
interface GigabitEthernet0/1
 ip mtu 1500
```

**Fix Option 2 - Ignore MTU for OSPF (use with caution):**
```
interface GigabitEthernet0/1
 ip ospf mtu-ignore
```

---

### Problem: OSPF Neighbor in INIT State

**Symptom:** Neighbor shows in INIT state (one-way hellos)

**Cause:** RTR-01 can hear RTR-02's hellos, but RTR-02 is not receiving RTR-01's hellos.

**Common Causes:**
- ACL blocking OSPF multicast (224.0.0.5)
- Interface duplex mismatch causing packet loss
- Physical layer issue (check interface error counters: `show interface Gi0/1`)

---

## Section 3: Automation Script Issues

### Problem: "Inventory file not found: devices.yml"

**Fix:** Create `devices.yml` in the project root from the template in README.md.

### Problem: "ModuleNotFoundError: No module named 'netmiko'"

**Fix:**
```bash
source venv/bin/activate    # Activate virtual environment
pip install -r requirements.txt
```

### Problem: Script completes but backup files are empty

**Cause:** Terminal paging (--More-- prompt) was not handled.

**Fix:** Netmiko handles this automatically via `send_command()`. If you're seeing empty files, ensure you're using `send_command("show running-config")` and NOT `send_command_timing()` for this command.

### Problem: Script hangs indefinitely on one device

**Cause:** The device may be presenting an unexpected prompt (e.g., "Do you want to continue? [yes]") that Netmiko is waiting for.

**Fix:** Add a timeout to the connection:
```python
# In connection_params, add:
"conn_timeout": 15,
"auth_timeout": 15,
```

---

## Section 4: Quick Reference Commands

```bash
# Verify SSH reachability from automation host
ssh -o StrictHostKeyChecking=no netadmin@192.168.100.1

# Test Netmiko connection manually
python3 -c "
from netmiko import ConnectHandler
d = {'device_type':'cisco_ios','host':'192.168.100.1','username':'netadmin','password':'YourPass'}
c = ConnectHandler(**d)
print(c.find_prompt())
c.disconnect()
"

# Run scripts with debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```
