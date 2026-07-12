# P2P Messenger VPN

Cross-platform peer-to-peer messenger with integrated VPN functionality.

## Description

P2P Messenger VPN is a decentralized communication tool that combines instant messaging with virtual private network capabilities. It allows users to create or join chat rooms over direct TCP connections, with optional password protection and built-in TUN/TAP-based VPN for virtual local networking.

## Features

- Peer-to-peer messaging over TCP with room-based architecture
- Integrated VPN via TUN/TAP virtual network interfaces
- UDP multicast room discovery
- SHA-256 password authentication for rooms
- Private messaging between specific users
- File transfer support
- Real-time typing indicators
- Desktop notifications and sound alerts
- Automatic ping measurement with PONG response
- Chat history logging
- Nickname mention highlighting
- Message and file transfer statistics
- ANSI-colored terminal interface

## Commands

| Command | Description |
|---------|-------------|
| /quit | Exit the chat room |
| /nick name | Change display nickname |
| /clear | Clear the terminal screen |
| /dice | Generate random number 1-6 |
| /ping | Measure round-trip latency |
| /stats | Display message and file count |
| /online | List connected peers |
| /msgto nick text | Send private message to user |
| /sendfile path | Send file to all room members |

## Requirements

- Python 3.8 or higher
- Linux: TUN/TAP kernel module, ip command
- Windows: OpenVPN TAP driver
- Root/administrator privileges for VPN functionality

## Installation

### Linux

git clone https://github.com/username/p2p-messenger-vpn.git
cd p2p-messenger-vpn
sudo bash setup.sh

The installer will detect your shell, check for Python 3, create a virtual environment, install dependencies, and create a system alias.

Run with:

sudo p2pmsngr

### Windows

Run setup.bat as Administrator, then execute C:\p2p_messenger_vpn\run.bat.

## Architecture

p2p_messenger_vpn/
    main.py           Application entry point
    cli_menu.py       Terminal user interface
    messenger.py      TCP messaging and authentication
    discovery.py      UDP multicast room scanner
    vpn.py            TUN/TAP interface management
    setup.sh          Linux installation script
    setup.bat         Windows installation script
    run.sh            Runtime launcher
    requirements.txt  Python dependencies

## Protocol

Room Discovery: UDP multicast on 224.0.0.187:48879. Hosts broadcast room name, nickname, and password hash every 2 seconds.

Connection: Client selects room, establishes TCP connection, sends authentication JSON with room name and SHA-256 password hash. Host validates and adds client to peer list.

Message Types: Type 1 for text, Type 2 for file transfer, Type 3 for VPN packets, Type 5 for private messages.

VPN: Each peer creates a TUN interface with a unique 10.x.x.1/24 address. VPN packets are encapsulated in TCP messages and broadcast to connected peers.
