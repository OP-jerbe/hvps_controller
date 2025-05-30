import socket
import sys
from pathlib import Path
from socket import SocketType
from typing import Optional


def get_root_dir() -> Path:
    if getattr(sys, 'frozen', False):  # Check if running from the PyInstaller EXE
        return Path(getattr(sys, '_MEIPASS', '.'))
    else:  # Running in a normal Python environment
        return Path(__file__).resolve().parents[1]


def open_socket(ip: str, port: int, timeout: float) -> SocketType | None:
    """Establishes a TCP connection"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        print(f'Socket open at {ip}:{port}')
        return sock
    except socket.error as e:
        print(f'Connection error: {e}')
        sock = None
        return sock


def close_socket(sock: Optional[SocketType]) -> None:
    """Closes the socket connection"""
    if sock:
        sock.close()
        print('Socket closed')
        sock = None
