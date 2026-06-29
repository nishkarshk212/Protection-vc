#!/usr/bin/env python3

import socket
import threading
import time
import collections
import random
import sys
from datetime import datetime, timedelta

try:
    import telebot
    from telebot import types
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️  Telegram bot features not available (pyTelegramBotAPI not installed)")

VERSION = "2.1.0"

print("=" * 100)
print(f"  🛡️ DDoS PROTECTION SYSTEM v{VERSION} - WITH /block COMMAND!")
print("=" * 100)

class DDoSProtection:
    def __init__(self):
        self.ip_traffic = collections.defaultdict(list)
        self.blocked_ips = set()
        self.whitelisted_ips = {"127.0.0.1", "192.168.1.1", "192.168.1.100"}
        self.alerts = []
        self.syn_threshold = 60
        self.icmp_threshold = 40
        self.connection_threshold = 150
        self.lock = threading.Lock()
        self.running = True
        self.stats = {
            "total_packets": 0,
            "total_blocked": 0,
            "attacks_detected": 0,
            "legitimate_requests": 0,
            "manual_blocks": 0,
            "start_time": datetime.now()
        }
        
        self.TOKEN = "8853038204:AAH9Fj0V2Gae27stnEiX3MlAYZxZumBzkB0"
        self.ADMIN_CHAT_ID = 3988638423
        self.bot = None
        if TELEGRAM_AVAILABLE:
            self.bot = telebot.TeleBot(self.TOKEN)
            self.setup_telegram_handlers()
    
    def setup_telegram_handlers(self):
        if not self.bot:
            return
        
        @self.bot.message_handler(commands=['start'])
        def send_welcome(message):
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("📊 Status", callback_data="status"),
                types.InlineKeyboardButton("🔔 Alerts", callback_data="alerts"),
                types.InlineKeyboardButton("🚫 Blocked", callback_data="blocked"),
                types.InlineKeyboardButton("🧪 Test", callback_data="test")
            )
            welcome = ("🛡️ <b>DDoS PROTECTION SYSTEM</b>\n\n"
                      "Commands:\n"
                      "/status - Check system status\n"
                      "/alerts - View recent alerts\n"
                      "/blocked - List blocked IPs\n"
                      "/block &lt;ip&gt; - Manually block an IP\n"
                      "/unblock &lt;ip&gt; - Unblock an IP\n"
                      "/test - Simulate DDoS attack\n"
                      "/help - Show this message")
            self.bot.send_message(message.chat.id, welcome, parse_mode="HTML", reply_markup=markup)
        
        @self.bot.message_handler(commands=['status'])
        def send_status(message):
            status = self.get_status()
            msg = (f"📊 <b>PROTECTION STATUS</b>\n\n"
                  f"📦 Total Packets: {status['total_packets']:,}\n"
                  f"✅ Legitimate: {status['legitimate_requests']:,}\n"
                  f"🎯 Attacks: {status['attacks_detected']}\n"
                  f"🚫 Blocked: {status['blocked_count']}\n"
                  f"🔒 Manual Blocks: {status['manual_blocks']}\n"
                  f"⏱️ Uptime: {status['uptime']}")
            self.bot.send_message(message.chat.id, msg, parse_mode="HTML")
        
        @self.bot.message_handler(commands=['alerts'])
        def send_alerts(message):
            alerts = self.alerts[-10:]
            if not alerts:
                self.bot.send_message(message.chat.id, "✅ No recent alerts")
                return
            msg = "🔔 <b>RECENT ALERTS</b>\n\n"
            for a in alerts:
                msg += f"• [{a['time']}] {a['ip']} - {a['threat_score']}%\n"
            self.bot.send_message(message.chat.id, msg, parse_mode="HTML")
        
        @self.bot.message_handler(commands=['blocked'])
        def send_blocked(message):
            blocked = list(self.blocked_ips)
            if not blocked:
                self.bot.send_message(message.chat.id, "✅ No blocked IPs")
                return
            msg = "🚫 <b>BLOCKED IPs</b>\n\n"
            for ip in blocked[:20]:
                msg += f"• {ip}\n"
            self.bot.send_message(message.chat.id, msg, parse_mode="HTML")
        
        @self.bot.message_handler(commands=['block'])
        def block_cmd(message):
            try:
                ip = message.text.split()[1]
                with self.lock:
                    if ip in self.whitelisted_ips:
                        self.bot.send_message(message.chat.id, f"⚠️ {ip} is whitelisted and cannot be blocked")
                    elif ip in self.blocked_ips:
                        self.bot.send_message(message.chat.id, f"⚠️ {ip} is already blocked")
                    else:
                        self.manual_block_ip(ip)
                        self.bot.send_message(message.chat.id, f"✅ Manually blocked: {ip}")
            except IndexError:
                self.bot.send_message(message.chat.id, "⚠️ Usage: /block &lt;ip&gt;")
            except Exception as e:
                self.bot.send_message(message.chat.id, f"❌ Error: {str(e)}")
        
        @self.bot.message_handler(commands=['unblock'])
        def unblock_cmd(message):
            try:
                ip = message.text.split()[1]
                with self.lock:
                    if ip in self.blocked_ips:
                        self.blocked_ips.remove(ip)
                        self.bot.send_message(message.chat.id, f"✅ Unblocked: {ip}")
                    else:
                        self.bot.send_message(message.chat.id, f"❌ {ip} not blocked")
            except:
                self.bot.send_message(message.chat.id, "⚠️ Usage: /unblock &lt;ip&gt;")
        
        @self.bot.message_handler(commands=['test'])
        def test_cmd(message):
            self.bot.send_message(message.chat.id, "🧪 Simulating DDoS attack...")
            test_ip = "10.0.0.99"
            for _ in range(100):
                self.analyze_packet(test_ip, pkt_type="SYN")
                time.sleep(0.01)
        
        @self.bot.message_handler(commands=['help'])
        def send_help(message):
            help_msg = ("🛡️ <b>DDoS PROTECTION HELP</b>\n\n"
                       "Available Commands:\n"
                       "/start - Start the bot\n"
                       "/status - Check system status\n"
                       "/alerts - View recent alerts\n"
                       "/blocked - List blocked IPs\n"
                       "/block &lt;ip&gt; - Manually block an IP\n"
                       "/unblock &lt;ip&gt; - Unblock an IP\n"
                       "/test - Simulate DDoS attack\n"
                       "/help - Show this message")
            self.bot.send_message(message.chat.id, help_msg, parse_mode="HTML")
        
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback(call):
            if call.data == "status": send_status(call.message)
            elif call.data == "alerts": send_alerts(call.message)
            elif call.data == "blocked": send_blocked(call.message)
            elif call.data == "test": test_cmd(call.message)
    
    def calculate_threat_score(self, ip):
        traffic = self.ip_traffic[ip]
        score = 0
        packet_count = len(traffic)
        
        if packet_count > self.syn_threshold:
            score += 50
        
        syn_packets = sum(1 for t, pt, p, s in traffic if pt == "SYN")
        if syn_packets > packet_count * 0.7:
            score += 30
        
        unique_ports = len(set(p for t, pt, p, s in traffic))
        if unique_ports > 20:
            score += 20
        
        avg_size = sum(s for t, pt, p, s in traffic) / max(packet_count, 1)
        if avg_size < 40 and packet_count > 30:
            score += 15
        
        return min(score, 150)
    
    def analyze_packet(self, ip, port=80, pkt_type="SYN", size=64):
        with self.lock:
            self.stats["total_packets"] += 1
            
            if ip in self.whitelisted_ips:
                self.stats["legitimate_requests"] += 1
                return False
            
            if ip in self.blocked_ips:
                return True
            
            now = datetime.now()
            self.ip_traffic[ip].append((now, pkt_type, port, size))
            
            cutoff = now - timedelta(seconds=12)
            self.ip_traffic[ip] = [
                (t, pt, p, s) for t, pt, p, s in self.ip_traffic[ip] if t > cutoff
            ]
            
            threat_score = self.calculate_threat_score(ip)
            
            if threat_score >= 100 and ip not in self.blocked_ips:
                self.block_ip(ip, threat_score, pkt_type)
                return True
            
            self.stats["legitimate_requests"] += 1
            return False
    
    def manual_block_ip(self, ip):
        """Manually block an IP address"""
        self.blocked_ips.add(ip)
        self.stats["total_blocked"] += 1
        self.stats["manual_blocks"] += 1
        
        alert = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "ip": ip,
            "threat_score": 100,
            "type": "MANUAL",
            "duration": "permanent"
        }
        self.alerts.append(alert)
        
        print(f"\n🔒 [MANUAL-BLOCK] {ip} | Duration: permanent")
        
        if self.bot:
            try:
                self.bot.send_message(
                    self.ADMIN_CHAT_ID,
                    f"🔒 <b>MANUAL BLOCK!</b>\nIP: {ip}\nDuration: permanent",
                    parse_mode="HTML"
                )
            except:
                pass
    
    def block_ip(self, ip, threat_score, pkt_type):
        self.blocked_ips.add(ip)
        self.stats["total_blocked"] += 1
        self.stats["attacks_detected"] += 1
        
        block_duration = min(threat_score, 300)
        
        alert = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "ip": ip,
            "threat_score": threat_score,
            "type": pkt_type,
            "duration": block_duration
        }
        self.alerts.append(alert)
        
        print(f"\n🚫 [AUTO-BLOCK] {ip} | Threat: {threat_score}% | Duration: {block_duration}s")
        
        if self.bot:
            try:
                self.bot.send_message(
                    self.ADMIN_CHAT_ID,
                    f"🚫 <b>DDoS BLOCKED!</b>\nIP: {ip}\nThreat: {threat_score}%\nDuration: {block_duration}s",
                    parse_mode="HTML"
                )
            except:
                pass
        
        threading.Thread(target=self.unblock_ip_after, args=(ip, block_duration)).start()
    
    def unblock_ip_after(self, ip, delay):
        time.sleep(delay)
        with self.lock:
            if ip in self.blocked_ips:
                self.blocked_ips.remove(ip)
                print(f"\n✅ [AUTO-UNBLOCK] {ip}")
    
    def get_status(self):
        uptime = datetime.now() - self.stats["start_time"]
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return {
            "total_packets": self.stats["total_packets"],
            "legitimate_requests": self.stats["legitimate_requests"],
            "attacks_detected": self.stats["attacks_detected"],
            "blocked_count": len(self.blocked_ips),
            "total_blocked": self.stats["total_blocked"],
            "manual_blocks": self.stats["manual_blocks"],
            "uptime": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            "blocked_ips": list(self.blocked_ips),
            "recent_alerts": self.alerts[-5:]
        }
    
    def display_status(self):
        status = self.get_status()
        print("\n" + "=" * 100)
        print("📊 REAL-TIME STATUS")
        print("=" * 100)
        print(f"   📦 Packets: {status['total_packets']:,} | ✅ Legitimate: {status['legitimate_requests']:,}")
        print(f"   🎯 Attacks: {status['attacks_detected']} | 🚫 Blocked: {status['blocked_count']}")
        print(f"   🔒 Manual Blocks: {status['manual_blocks']} | ⏱️ Uptime: {status['uptime']}")
        
        if status['blocked_ips']:
            print(f"\n   Blocked IPs: {', '.join(status['blocked_ips'][:5])}")
        
        if status['recent_alerts']:
            print(f"\n   Recent Alerts:")
            for a in status['recent_alerts']:
                print(f"   • [{a['time']}] {a['ip']} - {a['threat_score']}%")
    
    def _status_updater(self):
        while self.running:
            time.sleep(5)
            self.display_status()
    
    def _traffic_simulator(self):
        while self.running:
            legitimate_ips = ["192.168.1.10", "192.168.1.11", "192.168.1.12", "10.0.0.5"]
            
            for _ in range(random.randint(1, 4)):
                ip = random.choice(legitimate_ips)
                self.analyze_packet(ip, port=random.randint(80, 85), pkt_type="NORMAL")
            
            if random.random() < 0.20:
                attacker = f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
                print(f"\n⚠️  [DETECTED] Attack from: {attacker}")
                for _ in range(random.randint(70, 120)):
                    self.analyze_packet(attacker, port=random.randint(1, 10000), pkt_type="SYN", size=random.randint(20, 60))
                    time.sleep(0.005)
            
            time.sleep(random.uniform(0.5, 1.5))
    
    def start(self, with_telegram=True, with_simulation=True):
        print("\n🚀 [STARTING] DDoS Protection System with /block command")
        
        if with_telegram and self.bot:
            print("   • Telegram bot: ENABLED")
            print("   • /block command: AVAILABLE")
            threading.Thread(target=self._telegram_poller, daemon=True).start()
        else:
            print("   • Telegram bot: DISABLED")
        
        print("   • Auto-protection: ACTIVE")
        print("   • AI threat scoring: ENABLED")
        print("   • Real-time monitoring: ACTIVE")
        
        threading.Thread(target=self._status_updater, daemon=True).start()
        
        if with_simulation:
            print("   • Traffic simulation: ACTIVE")
            threading.Thread(target=self._traffic_simulator, daemon=True).start()
        
        print("\n" + "=" * 100)
        print("💡 System running! Press Ctrl+C to stop.")
        print("=" * 100)
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def _telegram_poller(self):
        if self.bot:
            try:
                self.bot.infinity_polling()
            except:
                pass
    
    def stop(self):
        self.running = False
        print("\n🛑 [STOPPED] System shutdown complete")
        print(f"   Final stats: {self.stats['attacks_detected']} attacks blocked!")
        print(f"   Manual blocks: {self.stats['manual_blocks']}")
        print("👋 Goodbye!")
        sys.exit(0)

def main():
    protection = DDoSProtection()
    protection.start(with_telegram=True, with_simulation=True)

if __name__ == "__main__":
    main()
