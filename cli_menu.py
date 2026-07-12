import os
import sys
import hashlib
import random
import string
import termios
import tty
import select
import time
import queue

class CLIMenu:
    def __init__(self):
        self.nickname = ""
        self.room_name = ""
        self.password = ""
        self.vpn_address = ""

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def get_key(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            if select.select([sys.stdin], [], [], 0.1)[0]:
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    if select.select([sys.stdin], [], [], 0)[0]:
                        ch2 = sys.stdin.read(1)
                        if ch2 == '[':
                            ch3 = sys.stdin.read(1)
                            if ch3 == 'A': return 'UP'
                            elif ch3 == 'B': return 'DOWN'
                            elif ch3 == 'C': return 'RIGHT'
                            elif ch3 == 'D': return 'LEFT'
                        else:
                            return 'ESC'
                    else:
                        return 'ESC'
                elif ch == '\r':
                    return 'ENTER'
                elif ch == '\x7f':
                    return 'BACKSPACE'
                elif ch == ' ':
                    return 'SPACE'
                elif ch == '\t':
                    return 'TAB'
                elif ch.isprintable():
                    return ch
                return ch
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def get_input(self, prompt=""):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            if prompt:
                sys.stdout.write(prompt)
                sys.stdout.flush()
            return input()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def draw_frame(self, title, content, footer=""):
        self.clear_screen()
        lines = content.split('\n')
        width = max(len(line) for line in lines) + 4
        if len(title) + 4 > width:
            width = len(title) + 4
        if len(footer) + 4 > width:
            width = len(footer) + 4
        width = min(width, 80)
        print("╔" + "═" * (width - 2) + "╗")
        print(f"║ {title.center(width - 4)} ║")
        print("╠" + "═" * (width - 2) + "╣")
        for line in lines:
            truncated = line[:width - 4]
            print(f"║ {truncated.ljust(width - 4)} ║")
        if footer:
            print("╠" + "═" * (width - 2) + "╣")
            print(f"║ {footer.center(width - 4)} ║")
        print("╚" + "═" * (width - 2) + "╝")

    def generate_vpn_address(self):
        return f"10.{random.randint(0,255)}.{random.randint(0,255)}.1"

    def setup_nickname(self):
        self.clear_screen()
        print("╔══════════════════════════════════════╗")
        print("║         НАСТРОЙКА ПРОФИЛЯ           ║")
        print("╠══════════════════════════════════════╣")
        print("║                                      ║")
        print("║  Введите ваш никнейм:                ║")
        print("║                                      ║")
        print("╚══════════════════════════════════════╝")
        nickname = self.get_input("→ ")
        if nickname.strip():
            self.nickname = nickname.strip()
        if not self.nickname:
            self.nickname = "User_" + ''.join(random.choices(string.ascii_letters + string.digits, k=4))

    def create_room_menu(self):
        room_name = ""
        has_password = False
        password = ""
        show_password = False
        cursor_pos = 0
        vpn_addr = self.generate_vpn_address()
        max_pos = 4
        while True:
            lines = ["СОЗДАНИЕ НОВОЙ КОМНАТЫ", ""]
            if cursor_pos == 0:
                lines.append(f">> Название комнаты: [{room_name}] <<")
            else:
                lines.append(f"   Название комнаты: [{room_name}]")
            lines.append("")
            if has_password:
                if cursor_pos == 1:
                    lines.append(f">> Пароль: [{(password if show_password else '*' * len(password))}] <<")
                else:
                    lines.append(f"   Пароль: [{(password if show_password else '*' * len(password))}]")
                if cursor_pos == 2:
                    lines.append(">> [X] Требовать пароль <<")
                else:
                    lines.append("   [X] Требовать пароль")
                if cursor_pos == 3:
                    lines.append(f">> [{('X' if show_password else ' ')}] Показать пароль <<")
                else:
                    lines.append(f"   [{('X' if show_password else ' ')}] Показать пароль")
            else:
                if cursor_pos == 1:
                    lines.append(">> Пароль: [не задан] <<")
                else:
                    lines.append("   Пароль: [не задан]")
                if cursor_pos == 2:
                    lines.append(">> [ ] Требовать пароль <<")
                else:
                    lines.append("   [ ] Требовать пароль")
            lines.append("")
            if cursor_pos == 4:
                lines.append(f">> VPN адрес: {vpn_addr} <<")
            else:
                lines.append(f"   VPN адрес: {vpn_addr}")
            lines.append("")
            lines.append("ENTER - подтвердить  |  ESC - назад")
            lines.append("СТРЕЛКИ - навигация  |  ПРОБЕЛ - переключить")
            self.draw_frame("СОЗДАТЬ КОМНАТУ", "\n".join(lines))
            key = None
            while key is None:
                key = self.get_key()
            if key == 'ENTER':
                if room_name.strip():
                    self.room_name = room_name.strip()
                    self.password = password if has_password else ""
                    self.vpn_address = vpn_addr
                    return True
            elif key == 'ESC':
                return False
            elif key == 'UP':
                cursor_pos = (cursor_pos - 1) % (max_pos + 1)
            elif key == 'DOWN':
                cursor_pos = (cursor_pos + 1) % (max_pos + 1)
            elif key == 'SPACE':
                if cursor_pos == 2:
                    has_password = not has_password
                    if not has_password:
                        password = ""
                        show_password = False
                elif cursor_pos == 3 and has_password:
                    show_password = not show_password
            elif key == 'BACKSPACE':
                if cursor_pos == 0 and room_name:
                    room_name = room_name[:-1]
                elif cursor_pos == 1 and has_password and password:
                    password = password[:-1]
            elif isinstance(key, str) and key.isprintable():
                if cursor_pos == 0:
                    room_name += key
                elif cursor_pos == 1 and has_password:
                    password += key

    def join_room_menu(self, rooms):
        if not rooms:
            self.draw_frame("ДОСТУПНЫЕ КОМНАТЫ", "Сканирование...\n\nКомнаты не найдены", "R - обновить  |  C - создать  |  ESC - назад")
            while True:
                key = self.get_key()
                if isinstance(key, str) and key.lower() == 'r':
                    return "refresh"
                elif isinstance(key, str) and key.lower() == 'c':
                    return "create"
                elif key == 'ESC':
                    return "back"
        selected = 0
        while True:
            lines = ["ДОСТУПНЫЕ КОМНАТЫ:", ""]
            if not rooms:
                lines.append("  (нет комнат)")
            else:
                for i, room in enumerate(rooms):
                    prefix = ">>" if i == selected else "  "
                    lock = "X" if room.get("has_password") else " "
                    lines.append(f"{prefix} [{lock}] {room['room']} ({room['host_nickname']})")
            lines.append("")
            lines.append("СТРЕЛКИ - навигация  |  ENTER - подключиться")
            lines.append("R - обновить  |  C - создать  |  ESC - назад")
            self.draw_frame("ПОДКЛЮЧЕНИЕ К КОМНАТЕ", "\n".join(lines))
            key = None
            while key is None:
                key = self.get_key()
            if key == 'UP':
                selected = (selected - 1) % max(1, len(rooms))
            elif key == 'DOWN':
                selected = (selected + 1) % max(1, len(rooms))
            elif key == 'ENTER':
                if rooms and selected < len(rooms):
                    return rooms[selected]
            elif isinstance(key, str) and key.lower() == 'r':
                return "refresh"
            elif isinstance(key, str) and key.lower() == 'c':
                return "create"
            elif key == 'ESC':
                return "back"

    def password_prompt(self, room_info):
        password = ""
        show_password = False
        error_msg = ""
        while True:
            lines = [
                f"Комната: {room_info['room']}",
                f"Хост: {room_info['host_nickname']}",
                "",
                f"Пароль: {(password if show_password else '*' * len(password)) if password else '_'}",
                f"Показать: [{'X' if show_password else ' '}] (TAB)",
                f"  {error_msg}" if error_msg else "",
                "",
                "ENTER - войти  |  ESC - назад"
            ]
            self.draw_frame("ВВОД ПАРОЛЯ", "\n".join(lines))
            key = None
            while key is None:
                key = self.get_key()
            if key == 'ENTER':
                if password:
                    if hashlib.sha256(password.encode()).hexdigest() == room_info.get("password_hash", ""):
                        return password
                    else:
                        error_msg = "НЕВЕРНЫЙ ПАРОЛЬ!"
                        password = ""
                else:
                    if not room_info.get("has_password"):
                        return ""
                    else:
                        error_msg = "ТРЕБУЕТСЯ ПАРОЛЬ!"
            elif key == 'ESC':
                return None
            elif key == 'TAB':
                show_password = not show_password
            elif key == 'BACKSPACE':
                password = password[:-1]
            elif isinstance(key, str) and key.isprintable():
                password += key

    def chat_interface(self, messenger, discovery, vpn, incoming_queue):
        message_buffer = ""
        messages = []
        while True:
            while not incoming_queue.empty():
                try:
                    msg = incoming_queue.get_nowait()
                    messages.append(msg)
                except queue.Empty:
                    break

            peers = discovery.get_peers()
            peer_list = [f"  {info['nickname']} ({ip})" for ip, info in peers.items()]
            if not peer_list:
                peer_list = ["  (ожидание пиров...)"]
            visible = messages[-15:] if len(messages) > 15 else messages
            lines = [
                f"Комната: {self.room_name}  |  VPN: {self.vpn_address}",
                "─" * 40
            ]
            for m in visible:
                lines.append(m[:60])
            lines.append("─" * 40)
            lines.append("Пиры:")
            lines.extend(peer_list[:5])
            lines.append("")
            lines.append(f"> {message_buffer}_")
            lines.append("")
            lines.append("ENTER - отправить  |  ESC - выход")
            self.draw_frame(f"ЧАТ ({self.nickname})", "\n".join(lines))
            key = None
            while key is None:
                key = self.get_key()
            if key == 'ENTER':
                if message_buffer.strip():
                    if message_buffer.startswith("/sendfile "):
                        filepath = message_buffer[10:].strip()
                        if messenger.send_file(filepath):
                            messages.append(f"[ВЫ] Файл отправлен: {os.path.basename(filepath)}")
                    else:
                        messenger.send_message(f"{self.nickname}: {message_buffer}")
                        messages.append(f"[ВЫ] {message_buffer}")
                    message_buffer = ""
            elif key == 'ESC':
                return "quit"
            elif key == 'BACKSPACE':
                message_buffer = message_buffer[:-1]
            elif isinstance(key, str) and key.isprintable():
                message_buffer += key

    def main_menu(self):
        while True:
            self.clear_screen()
            lines = [
                f"Добро пожаловать, {self.nickname}!",
                "",
                "[J] Присоединиться к комнате",
                "[C] Создать новую комнату",
                "[Q] Выход"
            ]
            self.draw_frame("P2P МЕССЕНДЖЕР С VPN", "\n".join(lines))
            key = None
            while key is None:
                key = self.get_key()
            if isinstance(key, str):
                kl = key.lower()
                if kl == 'j': return "join"
                elif kl == 'c': return "create"
                elif kl == 'q': return "quit"
