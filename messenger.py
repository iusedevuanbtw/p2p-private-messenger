import socket
import threading
import json
import struct
import time
import os
import hashlib

class Messenger:
    def __init__(self, nickname="User", tcp_port=0):
        self.nickname = nickname
        self.tcp_port = tcp_port
        self.running = False
        self.server_socket = None
        self.client_sockets = {}
        self.connections_lock = threading.Lock()
        self.message_callbacks = []
        self.file_transfer_callbacks = []
        self.vpn_packet_callbacks = []
        self.room_password_hash = ""

    def set_room_password(self, password):
        self.room_password_hash = hashlib.sha256(password.encode()).hexdigest() if password else ""

    def start_server(self, port=0):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', port))
        self.server_socket.listen(10)
        self.tcp_port = self.server_socket.getsockname()[1]
        self.running = True
        accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
        accept_thread.start()
        return self.tcp_port

    def _accept_connections(self):
        while self.running:
            try:
                client_sock, addr = self.server_socket.accept()
                client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                threading.Thread(target=self._handle_client, args=(client_sock, addr), daemon=True).start()
            except OSError:
                break

    def _handle_client(self, client_sock, addr):
        ip = addr[0]
        try:
            auth_data = self._recv_all(client_sock, 1024)
            if not auth_data:
                client_sock.close()
                return
            auth_msg = json.loads(auth_data.decode())
            if auth_msg.get("type") != "auth":
                client_sock.close()
                return
            if self.room_password_hash and auth_msg.get("password_hash") != self.room_password_hash:
                client_sock.close()
                return
            if auth_msg.get("room") != self.room_name:
                client_sock.close()
                return
        except (json.JSONDecodeError, UnicodeDecodeError):
            client_sock.close()
            return

        with self.connections_lock:
            self.client_sockets[ip] = client_sock
        try:
            while self.running:
                header = self._recv_all(client_sock, 8)
                if not header:
                    break
                msg_type, payload_len = struct.unpack('!II', header)
                payload = self._recv_all(client_sock, payload_len)
                if not payload:
                    break
                self._process_packet(ip, msg_type, payload)
        except (ConnectionError, OSError):
            pass
        finally:
            with self.connections_lock:
                if ip in self.client_sockets:
                    del self.client_sockets[ip]
            try:
                client_sock.close()
            except:
                pass

    def _recv_all(self, sock, n):
        data = b""
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

    def _process_packet(self, ip, msg_type, payload):
        if msg_type == 1:
            message = payload.decode('utf-8')
            for cb in self.message_callbacks:
                cb(ip, message)
        elif msg_type == 2:
            file_name_len = struct.unpack('!I', payload[:4])[0]
            file_name = payload[4:4 + file_name_len].decode('utf-8')
            file_data = payload[4 + file_name_len:]
            for cb in self.file_transfer_callbacks:
                cb(ip, file_name, file_data)
        elif msg_type == 3:
            for cb in self.vpn_packet_callbacks:
                cb(ip, payload)

    def connect_to_peer(self, ip, port, room_name, password_hash=""):
        if ip in self.client_sockets:
            return True
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(5)
        try:
            sock.connect((ip, port))
            auth = json.dumps({"type": "auth", "room": room_name, "password_hash": password_hash}).encode()
            sock.sendall(auth)
            sock.settimeout(None)
            with self.connections_lock:
                self.client_sockets[ip] = sock
            threading.Thread(target=self._handle_client, args=(sock, (ip, 0)), daemon=True).start()
            return True
        except (ConnectionError, socket.timeout, OSError):
            try:
                sock.close()
            except:
                pass
            return False

    def send_message(self, message, target_ip=None):
        payload = message.encode('utf-8')
        header = struct.pack('!II', 1, len(payload))
        self._broadcast(header + payload, target_ip)

    def send_file(self, filepath, target_ip=None):
        if not os.path.exists(filepath):
            return False
        filename = os.path.basename(filepath)
        with open(filepath, 'rb') as f:
            file_data = f.read()
        filename_encoded = filename.encode('utf-8')
        payload = struct.pack('!I', len(filename_encoded)) + filename_encoded + file_data
        header = struct.pack('!II', 2, len(payload))
        self._broadcast(header + payload, target_ip)
        return True

    def send_vpn_packet(self, packet_data, target_ip=None, exclude_ip=None):
        header = struct.pack('!II', 3, len(packet_data))
        self._broadcast(header + packet_data, target_ip, exclude_ip)

    def _broadcast(self, data, target_ip=None, exclude_ip=None):
        with self.connections_lock:
            if target_ip:
                targets = [sock for ip, sock in self.client_sockets.items() if ip == target_ip]
            else:
                targets = [sock for ip, sock in self.client_sockets.items() if ip != exclude_ip]
        for sock in targets:
            try:
                sock.sendall(data)
            except (ConnectionError, OSError):
                continue

    def add_message_callback(self, callback):
        self.message_callbacks.append(callback)

    def add_file_callback(self, callback):
        self.file_transfer_callbacks.append(callback)

    def add_vpn_callback(self, callback):
        self.vpn_packet_callbacks.append(callback)

    def stop(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        with self.connections_lock:
            for sock in self.client_sockets.values():
                try:
                    sock.close()
                except:
                    pass
            self.client_sockets.clear()
