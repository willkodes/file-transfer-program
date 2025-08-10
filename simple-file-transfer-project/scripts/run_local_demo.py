"""
run_local_demo.py
------------------
Convenience script to run BOTH:
- The TCP file receiving server (listens on 0.0.0.0:5001),
- The local HTTP front-end (UI) on http://127.0.0.1:8000.

This makes it easy to try immediately on one machine:
1) Run: python scripts/run_local_demo.py
2) Open: http://127.0.0.1:8000
3) Use Server IP: 127.0.0.1 and Port: 5001
4) Drag-and-drop a file and click Send.

For real two-computer demo:
- On receiver machine: run scripts/tcp_file_server.py (open firewall for port 5001).
- On sender machine: run scripts/http_frontend.py and in the UI set Server IP to the receiver's IP.
"""

import threading
import time

from tcp_file_server import start_server
from http_frontend import start_http_ui


def main():
    # Start TCP server in background
    t = threading.Thread(target=start_server, kwargs={"host": "0.0.0.0", "port": 5001}, daemon=True)
    t.start()
    time.sleep(0.3)

    # Start HTTP UI in foreground (blocking)
    start_http_ui(host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()