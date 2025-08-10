# Simple TCP File Transfer (Student Edition)

A minimal file transfer project with:
- Real TCP Socket transfer (no HTTP for file transport between sender and receiver),
- Browser front-end with Drag & Drop, progress, pause/resume,
- File validation and duplicate handling,
- No external libraries, only Python standard library.

## Quick Start (Single Machine Demo)

1. Run both services in one go:
   \`\`\`bash
   python scripts/run_local_demo.py
   \`\`\`
2. Open the UI:
   - http://127.0.0.1:8000
3. In the page:
   - Server IP: `127.0.0.1`
   - Server Port: `5001`
4. Drag and drop a file and click "Send".
5. Received files are saved in `scripts/received`.

## Two-Computer Setup

- On the receiving computer:
  \`\`\`bash
  python scripts/tcp_file_server.py
  \`\`\`
  - Make sure port `5001` is allowed by firewall.
- On the sending computer:
  \`\`\`bash
  python scripts/http_frontend.py
  \`\`\`
  - Open `http://localhost:8000` and set `Server IP` to the receiver's LAN IP (e.g., `192.168.1.10`), `Server Port` to `5001`.
  - Drag and drop a file and click "Send".

## Features

- Drag & Drop and click-to-select file
- Real-time progress bar and bytes sent
- Pause/Resume streaming upload from the browser
- Cancel upload
- Client-side file validation (size/type) plus server-side limits
- Duplicate handling on server: auto-renames like "file (1).ext"
- Success notifications (toast)
- Responsive layout, no frameworks

## Notes

- Browsers cannot open raw TCP sockets directly. This project uses a tiny local HTTP front-end
  to accept drag-and-drop from the browser and forward the bytes to the TCP server.
- All code is kept intentionally simple and heavily commented for education.
- Adjust validation in `shared.py`:
  - `MAX_FILE_SIZE_BYTES`
  - `ALLOWED_EXTENSIONS`
- Change listening ports in:
  - `tcp_file_server.py` (default 5001)
  - `http_frontend.py` (default 8000)

## Troubleshooting

- If you see connection errors, verify the TCP server is running and reachable at the given IP/port.
- On Windows/macOS, ensure firewall allows inbound connections on port 5001.
- Large files: Keep the demo limits reasonable for your classroom setting.
