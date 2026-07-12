import os
import sys
import struct
import threading
import subprocess

class VPNInterface:
    def __init__(self, address="10.0.0.1", netmask="255.0.0.0", mtu=1500):
        self.pid = os.getpid()
        self.name = f"p2pvpn{self.pid}"
        self.address = address
        self.netmask = netmask
        self.mtu = mtu
        self.tun_fd = None
        self.running = False
        self.read_thread = None
        self.on_packet_received = None
        self.adapter = None
        self.session = None

    def create_linux(self):
        import fcntl
        TUNSETIFF = 0x400454ca
        IFF_TUN = 0x0001
        IFF_NO_PI = 0x1000
        self.tun_fd = os.open("/dev/net/tun", os.O_RDWR)
        ifs = fcntl.ioctl(self.tun_fd, TUNSETIFF, struct.pack("16sH", self.name.encode(), IFF_TUN | IFF_NO_PI))
        ifname = ifs[:16].decode().strip('\x00')
        subprocess.run(["ip", "addr", "flush", "dev", ifname], stderr=subprocess.DEVNULL)
        subprocess.check_call(["ip", "link", "set", "dev", ifname, "up"])
        subprocess.check_call(["ip", "addr", "add", f"{self.address}/8", "dev", ifname])
        subprocess.check_call(["ip", "link", "set", "dev", ifname, "mtu", str(self.mtu)])
        return ifname

    def create_windows(self):
        try:
            import wintun
            self.adapter = wintun.WintunAdapter.create("P2P_VPN_Adapter", "Wintun")
            self.session = self.adapter.start_session()
            subprocess.check_call(["netsh", "interface", "ipv4", "set", "address",
                                   f"name={self.name}", "source=static",
                                   f"address={self.address}", f"mask={self.netmask}"])
            return self.name
        except ImportError:
            print("Windows требует библиотеку wintun-py. Установите: pip install wintun-py")
            print("VPN функционал недоступен.")
            self.tun_fd = None
            return self.name

    def start(self, on_packet_received):
        self.on_packet_received = on_packet_received
        if os.name == 'nt':
            self.create_windows()
            if self.session is None:
                return
        else:
            self.create_linux()
        self.running = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()

    def _read_loop(self):
        while self.running:
            try:
                if os.name == 'nt' and self.session:
                    packet = self.session.read_packet()
                    if packet and self.on_packet_received:
                        self.on_packet_received(packet)
                elif self.tun_fd:
                    packet = os.read(self.tun_fd, self.mtu)
                    if packet and self.on_packet_received:
                        self.on_packet_received(packet)
            except OSError:
                if self.running:
                    continue
                break

    def write(self, packet):
        try:
            if os.name == 'nt' and self.session:
                self.session.write_packet(packet)
            elif self.tun_fd:
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
        if os.name == 'nt':
            if self.session:
                try:
                    self.session.stop()
                except:
                    pass
            if self.adapter:
                try:
                    self.adapter.delete()
                except:
                    pass
        else:
            subprocess.run(["ip", "link", "del", self.name], stderr=subprocess.DEVNULL)
