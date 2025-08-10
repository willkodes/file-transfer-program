"""
shared.py
----------
Shared constants and helper utilities for the simple TCP file transfer project.
Only uses Python standard library to keep things simple for students.
"""

import os
import struct
import hashlib

# Network protocol constants
HEADER_LEN_SIZE = 8  # First 8 bytes tell how long the JSON header is
CHUNK_SIZE = 64 * 1024  # 64KB chunks for streaming

# Basic server-side validation (students can adjust as needed)
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB size limit example
# You can restrict extensions. Empty list means "allow all"
ALLOWED_EXTENSIONS = []  # e.g., ['.txt', '.png', '.jpg']


def pack_length(n: int) -> bytes:
    """
    Pack a Python int into 8 bytes (big-endian).
    The receiver uses this to know how big the JSON header is.
    """
    return struct.pack('!Q', n)


def unpack_length(b: bytes) -> int:
    """
    Unpack 8 bytes (big-endian) into a Python int.
    """
    return struct.unpack('!Q', b)[0]


def unique_save_path(dest_dir: str, filename: str) -> tuple[str, bool]:
    """
    Returns a unique path for saving a file.
    If a file with the same name exists, append ' (1)', ' (2)', ... before the extension.
    - dest_dir: output directory
    - filename: requested file name (no path)
    Returns (final_path, renamed_flag)
    """
    os.makedirs(dest_dir, exist_ok=True)
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(dest_dir, filename)
    counter = 1
    renamed = False

    while os.path.exists(candidate):
        candidate = os.path.join(dest_dir, f"{base} ({counter}){ext}")
        counter += 1
        renamed = True

    return candidate, renamed


def compute_sha256_of_file(path: str) -> str:
    """
    Compute SHA-256 of a file to demonstrate simple integrity check.
    NOTE: This is optional for the demo and can be omitted to simplify.
    """
    sha = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            block = f.read(CHUNK_SIZE)
            if not block:
                break
            sha.update(block)
    return sha.hexdigest()
