import os
import sys
import hashlib
import random
import time
import select
import termios
import tty
import datetime
import threading
from auth import register, login, get_rooms

COLORS = {
    'red': '\033[91m', 'green': '\033[92m', 'yellow': '\033[93m',
    'blue': '\033[94m', 'magenta': '\033[95m', 'cyan': '\033[96m',
    'white': '\033[97m', 'reset': '\033[0m', 'bold': '\033[1m',
    'gray': '\033[90m', 'bg_yellow': '\033[43m'
}

class CLIMenu:
    def __init__(self):
        self.nickname = ""
        self.room_name = ""
        self.password = ""
        self.vpn_address = ""
        self.unread = 0
        self.history_file = ""
        self.ping_start = 0
        self.typing = False
        self.last_activity = time.time()
        self.msg_count = 0
        self.file_count = 0
        self.logged_in = False
        self.host_mode = False

    def clear_screen(self):
        os.system('clear')

    def safe_input(self, prompt=""):
        sys.stdout.write(prompt)
        sys.stdout.flush()
        try:
            return sys.stdin.readline().strip()
        except:
            return ""

    def generate_vpn_address(self):
        return f"10.{random.randint(0,255)}.{random.randint(0,255)}.1"

    def auth_menu(self):
        while not self.logged_in:
            self.clear_screen()
            print(f"{COLORS['cyan']}╔══════════════════════════════╗{COLORS['reset']}")
            print(f"{COLORS['cyan']}║{COLORS['reset']}     {COLORS['bold']}АВТОРИЗАЦИЯ{COLORS['reset']}           {COLORS['cyan']}║{COLORS['reset']}")
            print(f"{COLORS['cyan']}╠══════════════════════════════╣{COLORS['reset']}")
            print(f"{COLORS['cyan']}║{COLORS['reset']} {COLORS['yellow']}1{COLORS['reset']}. {COLORS['bold']}Войти{COLORS['reset']}                    {COLORS['cyan']}║{COLORS['reset']}")
            print(f"{COLORS['cyan']}║{COLORS['reset']} {COLORS['yellow']}2{COLORS['reset']}. {COLORS['bold']}Регистрация{COLORS['reset']}              {COLORS['cyan']}║{COLORS['reset']}")
            print(f"{COLORS['cyan']}║{COLORS['reset']} {COLORS['yellow']}3{COLORS['reset']}. {COLORS['red']}Выход{COLORS['reset']}                    {COLORS['cyan']}║{COLORS['reset']}")
            print(f"{COLORS['cyan']}╚══════════════════════════════╝{COLORS['reset']}")
            choice = self.safe_input(f"{COLORS['green']}> {COLORS['reset']}")
            
            if choice == '1':
                u = self.safe_input(f"{COLORS['yellow']}Логин: {COLORS['reset']}")
                p = self.safe_input(f"{COLORS['yellow']}Пароль: {COLORS['reset']}")
                if login(u, p):
                    self.nickname = u
                    self.logged_in = True
                    print(f"{COLORS['green']}✓ Вход!{COLORS['reset']}")
                    time.sleep(1)
                else:
                    print(f"{COLORS['red']}✗ Неверно{COLORS['reset']}")
                    time.sleep(1)
            elif choice == '2':
                u = self.safe_input(f"{COLORS['yellow']}Логин: {COLORS['reset']}")
                p = self.safe_input(f"{COLORS['yellow']}Пароль: {COLORS['reset']}")
                if register(u, p):
                    self.nickname = u
                    self.logged_in = True
                    print(f"{COLORS['green']}✓ Аккаунт создан!{COLORS['reset']}")
                    time.sleep(1)
                else:
                    print(f"{COLORS['red']}✗ Занято{COLORS['reset']}")
                    time.sleep(1)
            elif choice == '3':
                sys.exit(0)

    def create_room_menu(self):
        vpn_addr = self.generate_vpn_address()
        self.clear_screen()
        print(f"{COLORS['cyan']}╔══════════════════════════════╗{COLORS['reset']}")
        print(f"{COLORS['cyan']}║{COLORS['reset']}     {COLORS['bold']}СОЗДАНИЕ КОМНАТЫ{COLORS['reset']}         {COLORS['cyan']}║{COLORS['reset']}")
        print(f"{COLORS['cyan']}╚══════════════════════════════╝{COLORS['reset']}")
        room_name = self.safe_input(f"{COLORS['yellow']}Название: {COLORS['reset']}")
        if not room_name.strip():
            return False
        password = self.safe_input(f"{COLORS['yellow']}Пароль (ENTER без): {COLORS['reset']}")
        self.room_name = room_name.strip()
        self.password = password.strip()
        self.vpn_address = vpn_addr
        self.history_file = f"{self.room_name}_log.txt"
        self.host_mode = True
        return True

    def join_room_menu(self, rooms):
        self.clear_screen()
        if not rooms:
            print(f"{COLORS['cyan']}╔══════════════════════════════╗{COLORS['reset']}")
            print(f"{COLORS['cyan']}║{COLORS['reset']}      {COLORS['bold']}ПОИСК КОМНАТ{COLORS['reset']}            {COLORS['cyan']}║{COLORS['reset']}")
            print(f"{COLORS['cyan']}╚══════════════════════════════╝{COLORS['reset']}")
            print(f"\n{COLORS['yellow']}Комнаты не найдены{COLORS['reset']}\n")
            print(f"[{COLORS['green']}R{COLORS['reset']}] Обновить  [{COLORS['green']}C{COLORS['reset']}] Создать  [{COLORS['red']}Q{COLORS['reset']}] Назад")
            choice = self.safe_input(f"{COLORS['green']}> {COLORS['reset']}")
            if choice.lower() == 'r': return "refresh"
            elif choice.lower() == 'c': return "create"
            else: return "back"
        
        print(f"{COLORS['cyan']}╔══════════════════════════════╗{COLORS['reset']}")
        print(f"{COLORS['cyan']}║{COLORS['reset']}    {COLORS['bold']}ДОСТУПНЫЕ КОМНАТЫ{COLORS['reset']}         {COLORS['cyan']}║{COLORS['reset']}")
        print(f"{COLORS['cyan']}╚══════════════════════════════╝{COLORS['reset']}\n")
        for i, r in enumerate(rooms):
            lock = f"{COLORS['red']}[X]{COLORS['reset']}" if r.get('password_hash') else f"{COLORS['green']}[ ]{COLORS['reset']}"
            host = f"{COLORS['bold']}{r.get('host_username','?')}{COLORS['reset']}"
            status = f"{COLORS['green']}🟢{COLORS['reset']}" if r.get('tcp_port') else f"{COLORS['red']}🔴{COLORS['reset']}"
            print(f"{COLORS['yellow']}{i+1}{COLORS['reset']}. {status} {lock} {COLORS['bold']}{r.get('name','?')}{COLORS['reset']} ({host})")
        print(f"\n[{COLORS['green']}R{COLORS['reset']}] Обновить  [{COLORS['green']}C{COLORS['reset']}] Создать  [{COLORS['red']}Q{COLORS['reset']}] Назад")
        choice = self.safe_input(f"{COLORS['green']}> {COLORS['reset']}")
        if choice.lower() == 'r': return "refresh"
        elif choice.lower() == 'c': return "create"
        elif choice.lower() == 'q': return "back"
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(rooms):
                room = rooms[idx]
                self.history_file = f"{room.get('name','room')}_log.txt"
                self.host_mode = False
                return room
        except: pass
        return "refresh"

    def password_prompt(self, room_info):
        if not room_info.get("password_hash"):
            return ""
        self.clear_screen()
        print(f"Комната: {room_info.get('name','?')}")
        password = self.safe_input(f"{COLORS['green']}Пароль: {COLORS['reset']}")
        if not password: return None
        if hashlib.sha256(password.encode()).hexdigest() == room_info.get("password_hash"):
            return password
        print(f"{COLORS['red']}✗ НЕВЕРНЫЙ ПАРОЛЬ!{COLORS['reset']}")
        time.sleep(1)
        return None

    def notify(self, msg):
        try:
            os.system(f"notify-send 'P2P Messenger' '{msg[:100]}' 2>/dev/null &")
        except:
            pass

    def typing_indicator(self, messenger):
        while True:
            if time.time() - self.last_activity < 3 and not self.typing:
                self.typing = True
                messenger.send_message(f"✏️ {self.nickname} печатает...")
            elif time.time() - self.last_activity >= 3 and self.typing:
                self.typing = False
            time.sleep(2)

    def chat_interface(self, messenger, vpn, incoming_queue):
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        
        self.clear_screen()
        print(f"{COLORS['cyan']}╔══════════════════════════════════════════╗{COLORS['reset']}")
        print(f"{COLORS['cyan']}║{COLORS['reset']}          {COLORS['bold']}P2P ЧАТ - {self.room_name}{COLORS['reset']}              {COLORS['cyan']}║{COLORS['reset']}")
        print(f"{COLORS['cyan']}╚══════════════════════════════════════════╝{COLORS['reset']}")
        print(f"{COLORS['gray']}/quit /nick /clear /dice /ping /stats /online /msgto Ник текст /hostto Ник{COLORS['reset']}")
        print(f"{COLORS['gray']}{'─'*50}{COLORS['reset']}\n")
        sys.stdout.flush()
        
        buffer = ""
        self.unread = 0
        self.msg_count = 0
        self.file_count = 0
        self.typing = False
        
        if self.history_file and os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    for line in f.readlines()[-50:]:
                        sys.stdout.write(line)
                sys.stdout.write(f"{COLORS['gray']}{'─'*50}{COLORS['reset']}\n")
            except:
                pass
        
        threading.Thread(target=self.typing_indicator, args=(messenger,), daemon=True).start()
        
        try:
            while True:
                while not incoming_queue.empty():
                    try:
                        msg = incoming_queue.get_nowait()
                        if "печатает" in msg:
                            sys.stdout.write(f"\r\033[K{COLORS['gray']}{msg}{COLORS['reset']}\n")
                            sys.stdout.write(f"\r\033[K{COLORS['green']}> {COLORS['reset']}{buffer}")
                            sys.stdout.flush()
                            continue
                        self.unread += 1
                        sys.stdout.write('\a')
                        self.notify(msg[:100])
                        timestamp = datetime.datetime.now().strftime('%H:%M')
                        if "PONG" in msg and self.ping_start > 0:
                            ping_time = int((time.time() - self.ping_start) * 1000)
                            sys.stdout.write(f"\r\033[K{COLORS['gray']}[{timestamp}]{COLORS['reset']} {msg} {COLORS['yellow']}({ping_time}ms){COLORS['reset']}\n")
                            self.ping_start = 0
                        elif "PING" in msg:
                            messenger.send_message(f"🏓 PONG от {self.nickname}")
                            sys.stdout.write(f"\r\033[K{COLORS['gray']}[{timestamp}]{COLORS['reset']} {msg} {COLORS['cyan']}(авто-PONG){COLORS['reset']}\n")
                        elif "ЛС от" in msg:
                            sys.stdout.write(f"\r\033[K{COLORS['magenta']}[{timestamp}] {msg}{COLORS['reset']}\n")
                        else:
                            if self.nickname.lower() in msg.lower():
                                sys.stdout.write(f"\r\033[K{COLORS['bg_yellow']}[{timestamp}] {msg}{COLORS['reset']}\n")
                            else:
                                sys.stdout.write(f"\r\033[K{COLORS['gray']}[{timestamp}]{COLORS['reset']} {msg}\n")
                        if self.history_file:
                            try:
                                with open(self.history_file, 'a') as f:
                                    f.write(f"[{timestamp}] {msg}\n")
                            except: pass
                    except:
                        break
                
                sys.stdout.write(f"\r\033[K{COLORS['green']}> {COLORS['reset']}{buffer}")
                sys.stdout.flush()
                
                r, _, _ = select.select([sys.stdin], [], [], 0.1)
                if not r:
                    continue
                
                self.last_activity = time.time()
                ch = sys.stdin.read(1)
                
                if ch in ('\r', '\n'):
                    msg = buffer
                    buffer = ""
                    sys.stdout.write('\r\n')
                    sys.stdout.flush()
                    if msg == "/quit":
                        return "quit"
                    elif msg == "/clear":
                        self.clear_screen()
                        print(f"{COLORS['cyan']}╔══════════════════════════════════════════╗{COLORS['reset']}")
                        print(f"{COLORS['cyan']}║{COLORS['reset']}          {COLORS['bold']}P2P ЧАТ - {self.room_name}{COLORS['reset']}              {COLORS['cyan']}║{COLORS['reset']}")
                        print(f"{COLORS['cyan']}╚══════════════════════════════════════════╝{COLORS['reset']}")
                        print(f"{COLORS['gray']}{'─'*50}{COLORS['reset']}\n")
                    elif msg == "/stats":
                        sys.stdout.write(f"{COLORS['yellow']}📊 Сообщений: {self.msg_count} | Файлов: {self.file_count}{COLORS['reset']}\n")
                    elif msg == "/online":
                        sys.stdout.write(f"{COLORS['green']}🟢 Онлайн:{COLORS['reset']}\n")
                        peers = messenger.get_peer_list()
                        if peers:
                            for ip, nick in peers.items():
                                sys.stdout.write(f"  {nick} ({ip})\n")
                        else:
                            sys.stdout.write(f"  {COLORS['gray']}Никого нет{COLORS['reset']}\n")
                    elif msg.startswith("/msgto "):
                        parts = msg[7:].split(" ", 1)
                        if len(parts) == 2:
                            target_nick = parts[0]
                            text = parts[1]
                            target_ip = messenger.find_peer_by_nick(target_nick)
                            if target_ip:
                                if messenger.send_message(text, target_nick=target_nick, target_ip=target_ip):
                                    sys.stdout.write(f"{COLORS['magenta']}[ВЫ → {target_nick}] {text}{COLORS['reset']}\n")
                                else:
                                    sys.stdout.write(f"{COLORS['red']}Не удалось отправить{COLORS['reset']}\n")
                            else:
                                sys.stdout.write(f"{COLORS['red']}Пользователь '{target_nick}' не найден{COLORS['reset']}\n")
                    elif msg.startswith("/hostto "):
                        target_nick = msg[8:].strip()
                        if target_nick:
                            messenger.send_message(f"🏠 Хост передается {target_nick} от {self.nickname}")
                            messenger.host_mode = False
                            sys.stdout.write(f"{COLORS['yellow']}🏠 Хост передан {target_nick}{COLORS['reset']}\n")
                        else:
                            sys.stdout.write(f"{COLORS['red']}Укажите ник: /hostto Ник{COLORS['reset']}\n")
                    elif msg.startswith("/nick "):
                        old_nick = self.nickname
                        self.nickname = msg[6:].strip()
                        sys.stdout.write(f"{COLORS['yellow']}Ник сменён: {old_nick} → {self.nickname}{COLORS['reset']}\n")
                    elif msg == "/dice":
                        dice = random.randint(1,6)
                        messenger.send_message(f"🎲 {self.nickname} бросает кубик: [{dice}]")
                        sys.stdout.write(f"{COLORS['yellow']}[ВЫ] Кубик: [{dice}]{COLORS['reset']}\n")
                        self.msg_count += 1
                    elif msg == "/ping":
                        self.ping_start = time.time()
                        messenger.send_message(f"🏓 PING от {self.nickname}")
                        sys.stdout.write(f"{COLORS['cyan']}[ВЫ] Пинг...{COLORS['reset']}\n")
                        self.msg_count += 1
                    elif msg.startswith("/sendfile "):
                        filepath = msg[10:].strip()
                        if messenger.send_file(filepath):
                            sys.stdout.write(f"{COLORS['green']}[ВЫ] Файл отправлен: {os.path.basename(filepath)}{COLORS['reset']}\n")
                            self.file_count += 1
                    elif msg.strip():
                        messenger.send_message(f"{COLORS['cyan']}{self.nickname}{COLORS['reset']}: {msg}")
                        sys.stdout.write(f"{COLORS['cyan']}[ВЫ]{COLORS['reset']} {msg}\n")
                        self.msg_count += 1
                    sys.stdout.flush()
                elif ch in ('\x7f', '\b') or ord(ch) == 127:
                    if buffer:
                        buffer = buffer[:-1]
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                elif ch == '\x03':
                    return "quit"
                elif ch == '\t':
                    buffer += "    "
                    sys.stdout.write("    ")
                    sys.stdout.flush()
                elif ch.isprintable() or ord(ch) >= 128:
                    buffer += ch
                    sys.stdout.write(ch)
                    sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def main_menu(self):
        while True:
            self.clear_screen()
            print(f"{COLORS['cyan']}╔══════════════════════════════╗{COLORS['reset']}")
            print(f"{COLORS['cyan']}║{COLORS['reset']}   {COLORS['bold']}P2P VPN МЕССЕНДЖЕР{COLORS['reset']}        {COLORS['cyan']}║{COLORS['reset']}")
            print(f"{COLORS['cyan']}╠══════════════════════════════╣{COLORS['reset']}")
            print(f"{COLORS['cyan']}║{COLORS['reset']} {COLORS['gray']}Пользователь:{COLORS['reset']} {COLORS['green']}{self.nickname:<14}{COLORS['reset']}{COLORS['cyan']}║{COLORS['reset']}")
            print(f"{COLORS['cyan']}╠══════════════════════════════╣{COLORS['reset']}")
            print(f"{COLORS['cyan']}║{COLORS['reset']} {COLORS['yellow']}1{COLORS['reset']}. {COLORS['bold']}Присоединиться{COLORS['reset']}           {COLORS['cyan']}║{COLORS['reset']}")
            print(f"{COLORS['cyan']}║{COLORS['reset']} {COLORS['yellow']}2{COLORS['reset']}. {COLORS['bold']}Создать комнату{COLORS['reset']}          {COLORS['cyan']}║{COLORS['reset']}")
            print(f"{COLORS['cyan']}║{COLORS['reset']} {COLORS['yellow']}3{COLORS['reset']}. {COLORS['red']}Выход{COLORS['reset']}                    {COLORS['cyan']}║{COLORS['reset']}")
            print(f"{COLORS['cyan']}╚══════════════════════════════╝{COLORS['reset']}")
            choice = self.safe_input(f"{COLORS['green']}> {COLORS['reset']}")
            if choice == '1': return "join"
            elif choice == '2': return "create"
            elif choice == '3': return "quit"
