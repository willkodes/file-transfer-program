"""
tcp_file_server.py
-------------------
A minimal TCP file receiver using Python's standard library.

Protocol:
1) Client connects via TCP.
2) Client sends 8 bytes for header length (big-endian uint64).
3) Client sends JSON header with:
   {
     "filename": str,   # base filename only, not path
     "filesize": int    # number of bytes that will follow
   }
4) Server checks validation and responds with a JSON message:
   - On OK: {"status":"OK","save_as":"<path_or_name>","message":"..."}
   - On Error: {"status":"ERROR","message":"reason"}
   This response is sent as 8-byte length + JSON bytes (same framing).
5) If OK, client streams exactly 'filesize' bytes.
6) Server writes bytes to a unique file path, then responds with final JSON:
   {"status":"DONE","saved_as":"<path>","bytes_received": n, "message":"Success"}
   Again framed with 8-byte length + JSON bytes.
7) Connection closes.

This server:
- Handles duplicate names by auto-renaming, e.g., "file (1).ext".
- Applies simple validation (size and extension).
- Prints progress logs in the console (for demonstration).
- Supports multiple concurrent clients using threads.

Run:
    python scripts/tcp_file_server.py
"""

import os
import json
import socket
import threading
from typing import Dict

from shared import (
    HEADER_LEN_SIZE,
    CHUNK_SIZE,
    MAX_FILE_SIZE_BYTES,
    ALLOWED_EXTENSIONS,
    pack_length,
    unpack_length,
    unique_save_path,
)

# Where received files are stored
RECEIVE_DIR = os.path.join(os.path.dirname(__file__), "received")


def recv_exactly(conn: socket.socket, n: int) -> bytes:
    """Receive exactly n bytes from the socket or raise if connection closes early."""
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Connection closed while reading")
        buf += chunk
    return buf


def send_json(conn: socket.socket, data: Dict):
    """Send JSON data framed by a 8-byte length header."""
    body = json.dumps(data).encode("utf-8")
    conn.sendall(pack_length(len(body)))
    conn.sendall(body)


def recv_json(conn: socket.socket) -> Dict:
    """Receive a framed JSON message (8-byte length + body)."""
    length_bytes = recv_exactly(conn, HEADER_LEN_SIZE)
    length = unpack_length(length_bytes)
    body = recv_exactly(conn, length)
    return json.loads(body.decode("utf-8"))


def validate_request(filename: str, filesize: int) -> tuple[bool, str]:
    """Basic server-side validation for safety."""
    if filesize < 0:
        return False, "Filesize must be non-negative."
    if filesize > MAX_FILE_SIZE_BYTES:
        return False, f"File too large. Limit is {MAX_FILE_SIZE_BYTES} bytes."
    if os.path.sep in filename or os.path.altsep and os.path.altsep in filename:
        return False, "Invalid filename."
    if ALLOWED_EXTENSIONS:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"Extension {ext} not allowed."
    return True, "OK"


def handle_client(conn: socket.socket, addr):
    """Handle a single client connection in its own thread."""
    try:
        print(f"[+] Connected from {addr}")

        # 1) Read header JSON
        header = recv_json(conn)
        filename = header.get("filename")
        filesize = int(header.get("filesize", -1))

        # 2) Validate
        is_ok, msg = validate_request(filename, filesize)
        if not is_ok:
            send_json(conn, {"status": "ERROR", "message": msg})
            print(f"[-] Validation error from {addr}: {msg}")
            return

        # 3) Compute unique save path (duplicate handling)
        save_path, renamed = unique_save_path(RECEIVE_DIR, filename)
        save_name_for_client = os.path.basename(save_path)

        # 4) Respond OK and the decided save name
        send_json(conn, {"status": "OK", "save_as": save_name_for_client, "message": "Ready to receive"})

        # 5) Receive file bytes
        bytes_remaining = filesize
        received = 0

        print(f"[>] Receiving '{filename}' ({filesize} bytes) from {addr} -> {save_path}")
        with open(save_path, "wb") as f:
            while bytes_remaining > 0:
                chunk = conn.recv(min(CHUNK_SIZE, bytes_remaining))
                if not chunk:
                    raise ConnectionError("Connection closed during file transfer")
                f.write(chunk)
                received += len(chunk)
                bytes_remaining -= len(chunk)

                # Print simple progress every ~1MB
                if received % (1024 * 1024) < CHUNK_SIZE:
                    pct = (received / filesize) * 100 if filesize else 100
                    print(f"    Progress: {received}/{filesize} bytes ({pct:.2f}%)")

        # 6) Final response
        final_msg = "Received successfully"
        send_json(
            conn,
            {
                "status": "DONE",
                "saved_as": save_name_for_client,
                "bytes_received": received,
                "renamed": renamed,
                "message": final_msg,
            },
        )
        print(f"[✓] Done '{filename}' from {addr} -> saved as '{save_name_for_client}'")

    except Exception as e:
        try:
            send_json(conn, {"status": "ERROR", "message": str(e)})
        except Exception:
            pass
        print(f"[!] Error with {addr}: {e}")
    finally:
        conn.close()
        print(f"[x] Disconnected {addr}")


def start_server(host: str = "0.0.0.0", port: int = 5001):
    """Start the TCP file receiver server."""
    print(f"TCP File Server listening on {host}:{port}")
    print(f"Files will be saved into: {RECEIVE_DIR}")
    print("Press Ctrl+C to stop.")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(5)
        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()


if __name__ == "__main__":
    # For classroom: change host/port here if needed
    start_server(host="0.0.0.0", port=5001)
