import json
import urllib.request
import hashlib

API_URL = "https://legacy-treadmill-posture.ngrok-free.dev"

def register(username, password):
    data = json.dumps({"username": username, "password": password}).encode()
    req = urllib.request.Request(f"{API_URL}/register", data=data, headers={"Content-Type": "application/json", "ngrok-skip-browser-warning": "1"})
    try:
        resp = json.loads(urllib.request.urlopen(req, timeout=5).read())
        return resp.get("success", False)
    except:
        return False

def login(username, password):
    data = json.dumps({"username": username, "password": password}).encode()
    req = urllib.request.Request(f"{API_URL}/login", data=data, headers={"Content-Type": "application/json", "ngrok-skip-browser-warning": "1"})
    try:
        resp = json.loads(urllib.request.urlopen(req, timeout=5).read())
        return resp.get("success", False)
    except:
        return False

def get_rooms():
    req = urllib.request.Request(f"{API_URL}/rooms", headers={"ngrok-skip-browser-warning": "1"})
    try:
        resp = json.loads(urllib.request.urlopen(req, timeout=5).read())
        data = resp.get("data", [])
        if data is None:
            return []
        return data
    except Exception as e:
        print(f"Ошибка получения комнат: {e}")
        return []

def create_room(name, host_username, password_hash, tcp_port, host_ip):
    data = json.dumps({"name": name, "host_username": host_username, "password_hash": password_hash, "tcp_port": tcp_port, "host_ip": host_ip}).encode()
    req = urllib.request.Request(f"{API_URL}/rooms", data=data, headers={"Content-Type": "application/json", "ngrok-skip-browser-warning": "1"})
    try:
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception as e:
        print(f"Ошибка создания комнаты: {e}")
        return False

def delete_room(name, username, password):
    req = urllib.request.Request(f"{API_URL}/rooms?name={name}&username={username}&password={password}", method="DELETE", headers={"ngrok-skip-browser-warning": "1"})
    try:
        urllib.request.urlopen(req, timeout=5)
        return True
    except:
        return False
