import os
import sys
import struct
import threading
import subprocess

if os.name == 'nt':
    import ctypes

class VPNInterface:
    def __init__(self, name="p2pvpn", address="10.0.0.1", netmask="255.255.255.0", mtu=1500):
        self.name = name
        self.address = address
        self.netmask = netmask
        self.mtu = mtu
        self.tun_fd = None
        self.running = False
        self.read_thread = None
        self.on_packet_received = None

    def create_linux(self):
        import fcntl
        TUNSETIFF = 0x400454ca
        IFF_TUN = 0x0001
        IFF_NO_PI = 0x1000
        self.tun_fd = os.open("/dev/net/tun", os.O_RDWR)
        ifs = fcntl.ioctl(self.tun_fd, TUNSETIFF, struct.pack("16sH", self.name.encode(), IFF_TUN | IFF_NO_PI))
        ifname = ifs[:16].decode().strip('\x00')
        subprocess.check_call(["ip", "link", "set", "dev", ifname, "up"])
        subprocess.check_call(["ip", "addr", "add", f"{self.address}/24", "dev", ifname])
        subprocess.check_call(["ip", "link", "set", "dev", ifname, "mtu", str(self.mtu)])
        return ifname

    def create_windows(self):
        print("Для Windows требуется установленный TAP-драйвер (OpenVPN).")
        print("Используйте wintun или установите драйвер вручную.")
        self.tun_fd = None
        return "p2pvpn"

    def start(self, on_packet_received):
        self.on_packet_received = on_packet_received
        if os.name == 'nt':
            self.create_windows()
            if self.tun_fd is None:
                raise RuntimeError("TUN интерфейс не создан")
        else:
            self.create_linux()
        self.running = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()

    def _read_loop(self):
        while self.running:
            try:
                if self.tun_fd is None:
                    break
                packet = os.read(self.tun_fd, self.mtu)
                if packet and self.on_packet_received:
                    self.on_packet_received(packet)
            except OSError:
                if self.running:
                    continue
                break

    def write(self, packet):
        try:
            if self.tun_fd:
                os.write(self.tun_fd, packet)
        except OSError:
            pass

    def stop(self):
        self.running = False
        if self.tun_fd:
            try:
                os.close(self.tun_fd)
            except:
                pass
        self.tun_fd = None
