import socket
import threading
import json
import struct
import os
import hashlib
import time

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
        self.room_name = ""
        self.host_mode = False

    def set_room_password(self, password):
        self.room_password_hash = hashlib.sha256(password.encode()).hexdigest() if password else ""

    def start_server(self, port=0):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', port))
        self.server_socket.listen(10)
        self.tcp_port = self.server_socket.getsockname()[1]
        self.running = True
        threading.Thread(target=self._accept_connections, daemon=True).start()
        return self.tcp_port

    def _accept_connections(self):
        while self.running:
            try:
                client_sock, addr = self.server_socket.accept()
                print(f"[TCP] Новое подключение от {addr[0]}:{addr[1]}")
                client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                threading.Thread(target=self._handle_client, args=(client_sock, addr[0]), daemon=True).start()
            except OSError as e:
                print(f"[TCP] Ошибка accept: {e}")
                break

    def _handle_client(self, client_sock, ip):
        try:
            raw = self._recv_json(client_sock)
            if not raw:
                client_sock.close()
                return
            auth_msg = json.loads(raw)
            print(f"[AUTH] {ip} -> {auth_msg}")
            if auth_msg.get("type") != "auth":
                client_sock.close()
                return
            if self.room_password_hash and auth_msg.get("password_hash") != self.room_password_hash:
                print(f"[AUTH] Неверный пароль от {ip}")
                client_sock.close()
                return
            if auth_msg.get("room") != self.room_name:
                print(f"[AUTH] Неверная комната от {ip}: {auth_msg.get('room')} != {self.room_name}")
                client_sock.close()
                return
            nickname = auth_msg.get("nickname", ip)
            print(f"[AUTH] {nickname} подключился из {ip}")
        except Exception as e:
            print(f"[AUTH] Ошибка: {e}")
            client_sock.close()
            return

        with self.connections_lock:
            self.client_sockets[ip] = {"sock": client_sock, "nickname": nickname, "ip": ip}
        self._read_loop(client_sock, ip)

    def _recv_json(self, sock):
        try:
            header = self._recv_exact(sock, 4)
            if not header:
                return None
            length = struct.unpack('!I', header)[0]
            if length > 1048576:
                return None
            data = self._recv_exact(sock, length)
            return data.decode('utf-8') if data else None
        except Exception as e:
            print(f"[RECV_JSON] Ошибка: {e}")
            return None

    def _recv_exact(self, sock, n):
        data = b""
        while len(data) < n:
            try:
                packet = sock.recv(n - len(data))
                if not packet:
                    return None
                data += packet
            except Exception as e:
                print(f"[RECV_EXACT] Ошибка: {e}")
                return None
        return data

    def _send_json(self, sock, obj):
        data = json.dumps(obj).encode('utf-8')
        header = struct.pack('!I', len(data))
        sock.sendall(header + data)

    def _read_loop(self, sock, key):
        try:
            while self.running:
                header = self._recv_exact(sock, 8)
                if not header:
                    print(f"[READ] {key} отключился")
                    break
                msg_type, payload_len = struct.unpack('!II', header)
                payload = self._recv_exact(sock, payload_len)
                if not payload:
                    break
                
                if msg_type == 1:
                    try:
                        message = payload.decode('utf-8')
                        print(f"[MSG] {key}: {message[:50]}...")
                        if self.host_mode and self.room_name:
                            log_file = f"{self.room_name}_log.txt"
                            try:
                                with open(log_file, 'a') as f:
                                    f.write(f"[{time.strftime('%H:%M')}] {message}\n")
                            except:
                                pass
                        for cb in self.message_callbacks:
                            cb(key, message)
                    except Exception as e:
                        print(f"[MSG] Ошибка: {e}")
                elif msg_type == 2:
                    try:
                        file_name_len = struct.unpack('!I', payload[:4])[0]
                        file_name = payload[4:4 + file_name_len].decode('utf-8')
                        file_data = payload[4 + file_name_len:]
                        print(f"[FILE] {key} -> {file_name} ({len(file_data)} байт)")
                        for cb in self.file_transfer_callbacks:
                            cb(key, file_name, file_data)
                    except Exception as e:
                        print(f"[FILE] Ошибка: {e}")
                elif msg_type == 3:
                    print(f"[VPN] Пакет от {key} ({len(payload)} байт)")
                    for cb in self.vpn_packet_callbacks:
                        cb(key, payload)
                elif msg_type == 5:
                    try:
                        whisper_data = json.loads(payload.decode('utf-8'))
                        from_nick = whisper_data.get("from", key)
                        text = whisper_data.get("text", "")
                        print(f"[WHISPER] {from_nick} -> {key}: {text}")
                        if self.host_mode and self.room_name:
                            log_file = f"{self.room_name}_log.txt"
                            try:
                                with open(log_file, 'a') as f:
                                    f.write(f"[{time.strftime('%H:%M')}] ЛС от {from_nick}: {text}\n")
                            except:
                                pass
                        for cb in self.message_callbacks:
                            cb(key, f"ЛС от {from_nick}: {text}")
                    except Exception as e:
                        print(f"[WHISPER] Ошибка: {e}")
        except Exception as e:
            print(f"[READ_LOOP] Ошибка: {e}")
        finally:
            with self.connections_lock:
                if key in self.client_sockets:
                    del self.client_sockets[key]
            try:
                sock.close()
            except:
                pass

    def connect_to_peer(self, ip, port, room_name, password_hash=""):
        if ip in self.client_sockets:
            print(f"[CONNECT] Уже подключен к {ip}")
            return True
        try:
            print(f"[CONNECT] Подключение к {ip}:{port}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(10)
            sock.connect((ip, port))
            print(f"[CONNECT] Соединение установлено")
            self._send_json(sock, {
                "type": "auth",
                "room": room_name,
                "password_hash": password_hash,
                "nickname": self.nickname
            })
            print(f"[CONNECT] Аутентификация отправлена")
            sock.settimeout(None)
            with self.connections_lock:
                self.client_sockets[ip] = {"sock": sock, "nickname": "host", "ip": ip}
            threading.Thread(target=self._read_loop, args=(sock, ip), daemon=True).start()
            return True
        except Exception as e:
            print(f"[CONNECT] Ошибка: {e}")
            try:
                sock.close()
            except:
                pass
            return False

    def send_message(self, message, target_nick=None, target_ip=None):
        if target_nick or target_ip:
            with self.connections_lock:
                for key, info in self.client_sockets.items():
                    if (target_nick and info["nickname"].lower() == target_nick.lower()) or \
                       (target_ip and key == target_ip):
                        try:
                            sock = info["sock"]
                            whisper = json.dumps({"from": self.nickname, "text": message})
                            payload = whisper.encode('utf-8')
                            header = struct.pack('!II', 5, len(payload))
                            sock.sendall(header + payload)
                            return True
                        except:
                            return False
            return False
        
        payload = message.encode('utf-8')
        header = struct.pack('!II', 1, len(payload))
        self._broadcast(header + payload)
        return True

    def send_file(self, filepath, target_nick=None, target_ip=None):
        if not os.path.exists(filepath):
            return False
        filename = os.path.basename(filepath)
        with open(filepath, 'rb') as f:
            file_data = f.read()
        filename_encoded = filename.encode('utf-8')
        payload = struct.pack('!I', len(filename_encoded)) + filename_encoded + file_data
        header = struct.pack('!II', 2, len(payload))
        
        if target_nick or target_ip:
            with self.connections_lock:
                for key, info in self.client_sockets.items():
                    if (target_nick and info["nickname"].lower() == target_nick.lower()) or \
                       (target_ip and key == target_ip):
                        try:
                            info["sock"].sendall(header + payload)
                            return True
                        except:
                            return False
            return False
        
        self._broadcast(header + payload)
        return True

    def send_vpn_packet(self, packet_data, exclude_ip=None):
        header = struct.pack('!II', 3, len(packet_data))
        self._broadcast(header + packet_data, exclude_ip)

    def _broadcast(self, data, exclude_ip=None):
        with self.connections_lock:
            targets = [(key, info["sock"]) for key, info in self.client_sockets.items() if key != exclude_ip]
        for key, sock in targets:
            try:
                sock.sendall(data)
            except Exception as e:
                print(f"[BROADCAST] Ошибка отправки к {key}: {e}")

    def add_message_callback(self, callback):
        self.message_callbacks.append(callback)

    def add_file_callback(self, callback):
        self.file_transfer_callbacks.append(callback)

    def add_vpn_callback(self, callback):
        self.vpn_packet_callbacks.append(callback)

    def get_peer_list(self):
        with self.connections_lock:
            return {key: info["nickname"] for key, info in self.client_sockets.items()}

    def find_peer_by_nick(self, nick):
        with self.connections_lock:
            for key, info in self.client_sockets.items():
                if info["nickname"].lower() == nick.lower():
                    return key
        return None

    def stop(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        with self.connections_lock:
            for info in self.client_sockets.values():
                try:
                    info["sock"].close()
                except:
                    pass
            self.client_sockets.clear()
