import socket
import json
import hashlib
import threading
import time
import struct

MULTICAST_GROUP = '224.0.0.187'
MULTICAST_PORT = 48879
BUFFER_SIZE = 4096

class RoomDiscovery:
    def __init__(self, nickname="User", room_name="DefaultRoom", password=""):
        self.nickname = nickname
        self.room_name = room_name
        self.password_hash = hashlib.sha256(password.encode()).hexdigest() if password else ""
        self.running = False
        self.peers = {}
        self.sock = None
        self.announce_thread = None
        self.listen_thread = None
        self.lock = threading.Lock()
        self.on_room_found = None
        self.tcp_port = 0
        self.listen_only = False

    def start(self, listen_only=False):
        self.listen_only = listen_only
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 2))
        mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        self.sock.bind(('', MULTICAST_PORT))
        self.sock.settimeout(0.5)
        self.running = True
        if not self.listen_only:
            self.announce_thread = threading.Thread(target=self._announce_loop, daemon=True)
            self.announce_thread.start()
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()

    def _announce_loop(self):
        announce_message = json.dumps({
            "type": "announce",
            "nickname": self.nickname,
            "room": self.room_name,
            "password_hash": self.password_hash,
            "tcp_port": self.tcp_port,
            "has_password": bool(self.password_hash)
        }).encode()
        while self.running:
            try:
                self.sock.sendto(announce_message, (MULTICAST_GROUP, MULTICAST_PORT))
                time.sleep(2)
            except OSError:
                break

    def _listen_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                message = json.loads(data.decode())
                if message.get("type") == "announce":
                    room_info = {
                        "room": message["room"],
                        "host_nickname": message["nickname"],
                        "host_ip": addr[0],
                        "tcp_port": message.get("tcp_port", 0),
                        "has_password": message.get("has_password", False),
                        "password_hash": message.get("password_hash", ""),
                        "last_seen": time.time()
                    }
                    if self.on_room_found:
                        self.on_room_found(room_info)
                    if not self.listen_only and message["room"] == self.room_name:
                        if not self.password_hash or message.get("password_hash") == self.password_hash:
                            with self.lock:
                                self.peers[addr[0]] = {
                                    "nickname": message["nickname"],
                                    "tcp_port": message.get("tcp_port", 0),
                                    "last_seen": time.time()
                                }
            except (json.JSONDecodeError, socket.timeout, OSError):
                continue

    def scan_rooms(self, duration=3):
        rooms = {}
        original_callback = self.on_room_found
        collected_rooms = {}

        def collect_room(room_info):
            key = f"{room_info['room']}_{room_info['host_ip']}"
            collected_rooms[key] = room_info

        self.on_room_found = collect_room
        time.sleep(duration)
        self.on_room_found = original_callback
        return list(collected_rooms.values())

    def get_peers(self):
        with self.lock:
            current_time = time.time()
            self.peers = {ip: info for ip, info in self.peers.items() if current_time - info["last_seen"] < 10}
            return dict(self.peers)

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
