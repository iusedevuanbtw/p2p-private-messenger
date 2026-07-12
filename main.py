import threading
import sys
import os
import time
import hashlib
import socket
import random
import queue
from vpn import VPNInterface
from discovery import RoomDiscovery
from messenger import Messenger
from cli_menu import CLIMenu

class P2PMessengerVPN:
    def __init__(self):
        self.cli = CLIMenu()
        self.messenger = None
        self.discovery = None
        self.vpn = None
        self.running = False
        self.incoming_queue = queue.Queue()

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
        self.incoming_queue.put(f"[{src_ip}] Файл: {filename} сохранён как {save_path}")

    def start(self):
        self.cli.setup_nickname()
        while True:
            action = self.cli.main_menu()
            if action == "quit":
                sys.exit(0)
            elif action == "create":
                if self.cli.create_room_menu():
                    self._start_services()
                    self.cli.chat_interface(self.messenger, self.discovery, self.vpn, self.incoming_queue)
                    self._stop_services()
            elif action == "join":
                self._join_room_flow()

    def _join_room_flow(self):
        temp_discovery = RoomDiscovery(self.cli.nickname, "", "")
        temp_discovery.start(listen_only=True)
        try:
            while True:
                rooms = temp_discovery.scan_rooms(duration=2)
                result = self.cli.join_room_menu(rooms)
                if result == "refresh":
                    continue
                elif result == "create":
                    temp_discovery.stop()
                    if self.cli.create_room_menu():
                        self._start_services()
                        self.cli.chat_interface(self.messenger, self.discovery, self.vpn, self.incoming_queue)
                        self._stop_services()
                    return
                elif result == "back":
                    break
                elif isinstance(result, dict):
                    room_info = result
                    password = ""
                    if room_info.get("has_password"):
                        password = self.cli.password_prompt(room_info)
                        if password is None:
                            continue
                    temp_discovery.stop()
                    self.cli.room_name = room_info["room"]
                    self.cli.password = password
                    self.cli.vpn_address = f"10.{random.randint(0,255)}.{random.randint(0,255)}.1"
                    self._start_services()
                    password_hash = hashlib.sha256(password.encode()).hexdigest() if password else ""
                    if self.messenger.connect_to_peer(room_info["host_ip"], room_info["tcp_port"], self.cli.room_name, password_hash):
                        self.cli.chat_interface(self.messenger, self.discovery, self.vpn, self.incoming_queue)
                    else:
                        self.incoming_queue.put("Не удалось подключиться к хосту.")
                    self._stop_services()
                    break
        finally:
            temp_discovery.stop()

    def _start_services(self):
        self.messenger = Messenger(self.cli.nickname)
        self.discovery = RoomDiscovery(self.cli.nickname, self.cli.room_name, self.cli.password)
        self.vpn = VPNInterface(name="p2pvpn", address=self.cli.vpn_address)
        self.messenger.set_room_password(self.cli.password)
        self.messenger.room_name = self.cli.room_name
        port = self.messenger.start_server()
        self.discovery.tcp_port = port
        self.messenger.add_vpn_callback(self._on_vpn_packet_received)
        self.messenger.add_message_callback(self._on_message_received)
        self.messenger.add_file_callback(self._on_file_received)
        self.discovery.start()
        self.vpn.start(self._on_tun_packet_received)
        self.running = True

    def _stop_services(self):
        self.running = False
        if self.discovery:
            self.discovery.stop()
        if self.messenger:
            self.messenger.stop()
        if self.vpn:
            self.vpn.stop()
        self.discovery = None
        self.messenger = None
        self.vpn = None
        self.incoming_queue = queue.Queue()

if __name__ == "__main__":
    app = P2PMessengerVPN()
    app.start()
