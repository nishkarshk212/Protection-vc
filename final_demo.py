#!/usr/bin/env python3.15

import socket
import threading
import time
import collections
from datetime import datetime, timedelta

print("=" * 80)
print("  🛡️ ALL-IN-ONE DDoS PROTECTION - FINAL DEMO")
print("=" * 80)

class AllInOneProtection:
    def __init__(self):
        self.ip_traffic = collections.defaultdict(list)
        self.blocked_ips = set()
        self.alerts = []
        self.lock = threading.Lock()
    
    def check(self, ip, pkt_type="SYN"):
        with self.lock:
            now = datetime.now()
            self.ip_traffic[ip].append(now)
            
            cutoff = now - timedelta(seconds=10)
            self.ip_traffic[ip] = [t for t in self.ip_traffic[ip] if t > cutoff]
            
            count = len(self.ip_traffic[ip])
            
            if count > 70 and ip not in self.blocked_ips:
                self.blocked_ips.add(ip)
                alert = f"🚫 BLOCKED: {ip} ({count} packets!)"
                self.alerts.append(alert)
                print(f"\n{alert}")
                threading.Thread(target=self.unblock, args=(ip,)).start()
                return True
            return False
    
    def unblock(self, ip):
        time.sleep(10)
        with self.lock:
            if ip in self.blocked_ips:
                self.blocked_ips.remove(ip)
                print(f"\n✅ UNBLOCKED: {ip}")

protection = AllInOneProtection()

print("\n📊 STEP 1: Normal traffic (legitimate users)...")
normal = ["192.168.1.10", "192.168.1.11", "192.168.1.12"]
for i in range(50):
    ip = normal[i % 3]
    protection.check(ip, "NORMAL")
    print(f"   ✓ {ip}", end="\r")
    time.sleep(0.05)
print("\n   ✅ Normal users safe!")

print("\n⚠️  STEP 2: DDoS attack simulation...")
attacker = "10.0.0.99"
print(f"   Attack from: {attacker}")
print("   Flooding...", end="", flush=True)
for i in range(150):
    if protection.check(attacker, "SYN"):
        break
    print(".", end="", flush=True)
    time.sleep(0.01)

print("\n" + "=" * 80)
print("🎉 EVERYTHING MERGED AND WORKING!")
print("=" * 80)
print(f"\n📊 Results:")
print(f"   Blocked IPs: {len(protection.blocked_ips)}")
print(f"   Total Alerts: {len(protection.alerts)}")
print(f"\n   Alerts: {', '.join(protection.alerts)}")

print("\n💡 All functions merged into one:")
print("   • Auto-detection ✓")
print("   • Auto-protection ✓")
print("   • Auto-block ✓")
print("   • Auto-unblock ✓")
print("   • All-in-one file ✓")

print("\n🚀 To use main.py for full interactive system!")
print("=" * 80)
