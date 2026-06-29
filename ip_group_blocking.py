#!/usr/bin/env python3.15

import socket
import threading
import time
import collections
from datetime import datetime, timedelta
import ipaddress

print("=" * 100)
print("  🛡️ IP GROUP DETECTION & BLOCKING SYSTEM")
print("=" * 100)

class IPGroupProtection:
    def __init__(self):
        self.ip_traffic = collections.defaultdict(list)
        self.blocked_ips = set()
        self.blocked_subnets = set()
        self.alerts = []
        self.lock = threading.Lock()
        self.single_ip_threshold = 70
        self.subnet_threshold = 150
        self.subnet_size = 24
    
    def ip_to_subnet(self, ip):
        try:
            network = ipaddress.ip_network(f"{ip}/{self.subnet_size}", strict=False)
            return str(network)
        except:
            return None
    
    def get_subnet_traffic(self, subnet):
        count = 0
        for ip, traffic in self.ip_traffic.items():
            if self.ip_to_subnet(ip) == subnet:
                count += len(traffic)
        return count
    
    def analyze(self, ip, pkt_type="SYN"):
        with self.lock:
            now = datetime.now()
            self.ip_traffic[ip].append(now)
            
            cutoff = now - timedelta(seconds=10)
            self.ip_traffic[ip] = [t for t in self.ip_traffic[ip] if t > cutoff]
            
            ip_count = len(self.ip_traffic[ip])
            subnet = self.ip_to_subnet(ip)
            subnet_count = self.get_subnet_traffic(subnet) if subnet else 0
            
            if subnet and subnet_count > self.subnet_threshold and subnet not in self.blocked_subnets:
                self.block_subnet(subnet, subnet_count)
                return True
            
            if ip_count > self.single_ip_threshold and ip not in self.blocked_ips:
                self.block_ip(ip, ip_count)
                return True
            
            return False
    
    def block_ip(self, ip, count):
        self.blocked_ips.add(ip)
        alert = f"🚫 BLOCKED IP: {ip} ({count} packets)"
        self.alerts.append(alert)
        print(f"\n{alert}")
        threading.Thread(target=self.unblock_ip, args=(ip,)).start()
    
    def block_subnet(self, subnet, count):
        self.blocked_subnets.add(subnet)
        alert = f"🚫🚫 BLOCKED SUBNET: {subnet} ({count} total packets from this range!)"
        self.alerts.append(alert)
        print(f"\n{alert}")
        threading.Thread(target=self.unblock_subnet, args=(subnet,)).start()
    
    def unblock_ip(self, ip):
        time.sleep(15)
        with self.lock:
            if ip in self.blocked_ips:
                self.blocked_ips.remove(ip)
                print(f"\n✅ UNBLOCKED IP: {ip}")
    
    def unblock_subnet(self, subnet):
        time.sleep(30)
        with self.lock:
            if subnet in self.blocked_subnets:
                self.blocked_subnets.remove(subnet)
                print(f"\n✅ UNBLOCKED SUBNET: {subnet}")
    
    def is_blocked(self, ip):
        with self.lock:
            if ip in self.blocked_ips:
                return True
            subnet = self.ip_to_subnet(ip)
            if subnet and subnet in self.blocked_subnets:
                return True
            return False
    
    def get_status(self):
        with self.lock:
            return {
                "blocked_ips": list(self.blocked_ips),
                "blocked_subnets": list(self.blocked_subnets),
                "total_blocked": len(self.blocked_ips) + len(self.blocked_subnets),
                "alerts": self.alerts[-10:]
            }

protection = IPGroupProtection()

print("\n📊 [1/3] Normal traffic from different subnets...")
normal_ips = [
    "192.168.1.10", "192.168.1.11", "192.168.1.12",
    "10.0.0.5", "10.0.0.6", "172.16.0.10"
]
for i in range(60):
    ip = normal_ips[i % 6]
    protection.analyze(ip, "NORMAL")
    print(f"   ✓ {ip}", end="\r")
    time.sleep(0.04)
print("\n   ✅ Normal traffic from multiple subnets - safe!")

print("\n⚠️  [2/3] DDoS from a SINGLE IP...")
single_attacker = "45.33.32.156"
print(f"   Attack from: {single_attacker}")
print("   Flooding...", end="", flush=True)
for i in range(150):
    if protection.analyze(single_attacker, "SYN"):
        break
    print(".", end="", flush=True)
    time.sleep(0.01)

print("\n\n⚠️  [3/3] DDoS from MULTIPLE IPs in the SAME SUBNET (group attack)...")
subnet_attackers = [
    "185.220.101.10", "185.220.101.11", "185.220.101.12",
    "185.220.101.13", "185.220.101.14", "185.220.101.15"
]
print(f"   Attacking subnet: 185.220.101.0/{protection.subnet_size}")
print(f"   Attackers: {', '.join(subnet_attackers)}")
print("   Coordinated flood from multiple IPs in same group...")
for round_num in range(5):
    for ip in subnet_attackers:
        for _ in range(10):
            protection.analyze(ip, "SYN")
            time.sleep(0.001)
    time.sleep(0.2)

print("\n" + "=" * 100)
print("📊 FINAL RESULTS")
print("=" * 100)
status = protection.get_status()
print(f"\n🚫 Blocked IPs: {len(status['blocked_ips'])}")
if status['blocked_ips']:
    print(f"   {', '.join(status['blocked_ips'])}")

print(f"\n🚫🚫 Blocked Subnets (Groups): {len(status['blocked_subnets'])}")
if status['blocked_subnets']:
    print(f"   {', '.join(status['blocked_subnets'])}")

print(f"\n🔔 Total Alerts: {len(status['alerts'])}")
for alert in status['alerts']:
    print(f"   {alert}")

print("\n💡 How to find & block group IPs:")
print("=" * 100)
print("   1. Identify the subnet (e.g., /24 means first 3 numbers same)")
print("      Example: 192.168.1.10 → subnet 192.168.1.0/24")
print("   2. Count total traffic from all IPs in that subnet")
print("   3. If threshold exceeded, block the ENTIRE subnet")
print("   4. This stops coordinated attacks from multiple IPs in same group")
print("\n   Subnet sizes:")
print("   • /8:  16.7 million IPs (big group)")
print("   • /16: 65,536 IPs (medium group)")
print("   • /24: 256 IPs (small group - what we used)")
print("   • /32: single IP (not a group)")

print("\n✅ DONE!")
print("=" * 100)
