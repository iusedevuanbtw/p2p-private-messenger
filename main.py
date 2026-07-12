import threading
import sys
import os
import time
import hashlib
import random
import queue
import requests
import socket
from vpn import VPNInterface
from discovery import RoomDiscovery
from messenger import Messenger
from cli_menu import CLIMenu
from auth import create_room as api_create_room, delete_room, get_rooms

class P2PMessengerVPN:
    def __init__(self):
        self.cli = CLIMenu()
        self.messenger = None
        self.discovery = None
        self.vpn = None
        self.running = False
        self.incoming_queue = queue.Queue()
        self.public_ip = None
        self.heartbeat_thread = None
        self.heartbeat_running = False

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"

    def _get_public_ip(self):
        try:
            public_ip = requests.get('https://api.ipify.org', timeout=5).text
            local_ip = self._get_local_ip()
            if public_ip == local_ip:
                self.public_ip = local_ip
                print(f"[IP] Использую локальный: {local_ip}")
            else:
                self.public_ip = public_ip
                print(f"[IP] Использую публичный: {public_ip}")
        except:
            self.public_ip = self._get_local_ip()
            print(f"[IP] Ошибка, использую локальный: {self.public_ip}")

    def _heartbeat_loop(self):
        while self.heartbeat_running:
            if self.cli.host_mode and self.messenger:
                try:
                    requests.post(f"{API_URL}/heartbeat?room={self.cli.room_name}&host={self.cli.nickname}", timeout=2)
                except:
                    pass
            time.sleep(5)

    def _on_vpn_packet_received(self, src_ip, packet):
        if self.vpn:
            self.vpn.write(packet)

    def _on_tun_packet_received(self, packet):
        if self.messenger:
            self.messenger.send_vpn_packet(packet, exclude_ip=None)

    def _on_message_received(self, src_ip, message):
        self.incoming_queue.put(f"[{src_ip}] {message}")

    def _on_file_received(self, src_ip, filename, file_data):
        save_path = f"received_{filename}"
        with open(save_path, 'wb') as f:
            f.write(file_data)
        self.incoming_queue.put(f"[{src_ip}] Файл: {filename} -> {save_path}")

    def start(self):
        self.cli.auth_menu()
        while True:
            action = self.cli.main_menu()
            if action == "quit":
                sys.exit(0)
            elif action == "create":
                if self.cli.create_room_menu():
                    self._get_public_ip()
                    self._start_services()
                    self._publish_room_to_server()
                    self.cli.chat_interface(self.messenger, self.vpn, self.incoming_queue)
                    self._stop_services()
            elif action == "join":
                self._join_room_flow()

    def _publish_room_to_server(self):
        if self.cli.host_mode and self.messenger:
            port = self.messenger.tcp_port
            password_hash = hashlib.sha256(self.cli.password.encode()).hexdigest() if self.cli.password else ""
            print(f"[PUBLISH] Комната: {self.cli.room_name}, Порт: {port}, IP: {self.public_ip}")
            api_create_room(
                name=self.cli.room_name,
                host_username=self.cli.nickname,
                password_hash=password_hash,
                tcp_port=port,
                host_ip=self.public_ip
            )
            self.heartbeat_running = True
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()

    def _join_room_flow(self):
        while True:
            rooms = get_rooms()
            print(f"[ROOMS] Получено комнат: {len(rooms)}")
            
            # Удаляем комнаты без хоста (нет heartbeat)
            active_rooms = []
            for r in rooms:
                host_ip = r.get('host_ip')
                tcp_port = r.get('tcp_port')
                if host_ip and tcp_port:
                    # Проверяем доступность
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    try:
                        sock.connect((host_ip, tcp_port))
                        sock.close()
                        active_rooms.append(r)
                        print(f"  + {r.get('name')} | {r.get('host_username')} | {host_ip}:{tcp_port} (active)")
                    except:
                        print(f"  - {r.get('name')} | {r.get('host_username')} | {host_ip}:{tcp_port} (offline)")
                else:
                    print(f"  ? {r.get('name')} | {r.get('host_username')} | invalid data")
            
            result = self.cli.join_room_menu(active_rooms if active_rooms else rooms)
            if result == "refresh":
                continue
            elif result == "create":
                if self.cli.create_room_menu():
                    self._get_public_ip()
                    self._start_services()
                    self._publish_room_to_server()
                    self.cli.chat_interface(self.messenger, self.vpn, self.incoming_queue)
                    self._stop_services()
                return
            elif result == "back":
                break
            elif isinstance(result, dict):
                room_info = result
                password = ""
                if room_info.get("password_hash"):
                    password = self.cli.password_prompt(room_info)
                    if password is None:
                        continue
                
                if room_info.get("host_username") == self.cli.nickname:
                    print("[SKIP] Это ваша комната, ожидайте подключения других")
                    time.sleep(2)
                    continue
                
                self.cli.room_name = room_info.get("name", "room")
                self.cli.password = password
                self.cli.vpn_address = f"10.{random.randint(0,255)}.{random.randint(0,255)}.1"
                self.cli.host_mode = False
                self._start_services()
                password_hash = hashlib.sha256(password.encode()).hexdigest() if password else ""
                host_ip = room_info.get("host_ip", "0.0.0.0")
                tcp_port = room_info.get("tcp_port", 0)
                
                local_ip = self._get_local_ip()
                if host_ip == local_ip or host_ip == "127.0.0.1":
                    host_ip = "127.0.0.1"
                    print(f"[CONNECT] Подключаюсь к локальному хосту")
                
                print(f"[CONNECT] Пытаюсь подключиться к {host_ip}:{tcp_port}")
                
                if self.messenger.connect_to_peer(host_ip, tcp_port, self.cli.room_name, password_hash):
                    print("[CONNECT] Успешно подключено!")
                    self.cli.chat_interface(self.messenger, self.vpn, self.incoming_queue)
                else:
                    print("[CONNECT] Ошибка подключения!")
                    self.incoming_queue.put("Не удалось подключиться к хосту.")
                    time.sleep(2)
                self._stop_services()
                break

    def _start_services(self):
        self.messenger = Messenger(self.cli.nickname)
        self.discovery = RoomDiscovery(self.cli.nickname, self.cli.room_name, self.cli.password)
        self.vpn = VPNInterface(address=self.cli.vpn_address)
        self.messenger.set_room_password(self.cli.password)
        self.messenger.room_name = self.cli.room_name
        self.messenger.host_mode = self.cli.host_mode
        port = self.messenger.start_server(0)
        print(f"[SERVER] Запущен на порту: {port}")
        self.discovery.tcp_port = port
        self.messenger.add_vpn_callback(self._on_vpn_packet_received)
        self.messenger.add_message_callback(self._on_message_received)
        self.messenger.add_file_callback(self._on_file_received)
        self.discovery.start()
        self.vpn.start(self._on_tun_packet_received)
        self.running = True

    def _stop_services(self):
        self.running = False
        self.heartbeat_running = False
        if self.cli.host_mode and self.cli.room_name:
            delete_room(self.cli.room_name, self.cli.nickname, self.cli.password)
        if self.discovery:
            self.discovery.stop()
        if self.messenger:
            self.messenger.stop()
        if self.vpn:
            self.vpn.stop()
        self.discovery = None
        self.messenger = None
        self.vpn = None
        while not self.incoming_queue.empty():
            try:
                self.incoming_queue.get_nowait()
            except queue.Empty:
                break

if __name__ == "__main__":
    app = P2PMessengerVPN()
    app.start()
