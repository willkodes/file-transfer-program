"""
http_frontend.py (chunked session version)
------------------------------------------
A tiny local HTTP server that:
- Serves a simple web UI with drag-and-drop and progress,
- Uses a session-based, chunked upload over multiple small POSTs (no streaming body),
- Forwards all bytes over a single, real TCP socket to the TCP file server (tcp_file_server.py).

Endpoints:
- POST /begin?host=IP&port=PORT    (headers: X-Filename, X-Filesize)
    -> connects to TCP server, sends header, awaits OK, returns {session_id, save_as}
- POST /chunk?id=SESSION_ID        (body: raw binary chunk)
    -> forwards chunk to TCP socket, returns {received, remaining}
- POST /end?id=SESSION_ID
    -> waits for final DONE from TCP server, returns it and closes session
- POST /cancel?id=SESSION_ID
    -> closes session

Run:
    python scripts/http_frontend.py
Open:
    http://127.0.0.1:8000

This version avoids streaming request bodies, so it works reliably on Chrome/Windows without duplex.
Only Python standard library is used.
"""

import json
import socket
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

from shared import HEADER_LEN_SIZE, CHUNK_SIZE, pack_length, unpack_length

# In-memory session store: session_id -> dict
SESSIONS = {}
SESSIONS_LOCK = threading.Lock()

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Simple TCP File Transfer (Student Edition)</title>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <style>
    :root {
      --bg: #0f172a; --panel: #111827; --accent: #10b981; --accent-600: #059669;
      --muted: #9ca3af; --text: #e5e7eb; --card: #0b1220; --border: #1f2937;
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, Helvetica Neue, Arial;
           background: var(--bg); color: var(--text); min-height: 100vh; display: grid; place-items: center; padding: 24px; }
    .container { width: 100%; max-width: 720px; background: var(--panel); border: 1px solid var(--border);
                 border-radius: 12px; padding: 20px; display: grid; gap: 16px; }
    header h1 { margin: 0 0 4px; font-size: 20px; }
    header p { margin: 0; color: var(--muted); font-size: 14px; }
    .grid { display: grid; grid-template-columns: 1fr; gap: 12px; }
    @media (min-width: 640px) { .grid-2 { grid-template-columns: 1fr 1fr; } }
    label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 4px; }
    input[type="text"], input[type="number"] { width: 100%; background: var(--card); border: 1px solid var(--border);
      color: var(--text); border-radius: 8px; padding: 10px 12px; outline: none; }
    input[type="text"]:focus, input[type="number"]:focus { border-color: var(--accent); }
    .dropzone { background: var(--card); border: 2px dashed var(--border); border-radius: 12px; padding: 20px; text-align: center;
      color: var(--muted); transition: border-color .2s, background .2s; cursor: pointer; }
    .dropzone.dragover { border-color: var(--accent); background: #0c1729; }
    .file-info { font-size: 14px; color: var(--text); opacity: .9; }
    .hint { font-size: 12px; color: var(--muted); }
    .progress-wrap { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 14px; display: grid; gap: 8px; }
    .bar { height: 12px; background: #0b1325; border: 1px solid var(--border); border-radius: 999px; overflow: hidden; }
    .bar > span { display: block; height: 100%; width: 0%; background: linear-gradient(90deg, var(--accent), var(--accent-600)); transition: width .1s; }
    .stats { display: flex; justify-content: space-between; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace;
      font-size: 12px; color: var(--muted); }
    .buttons { display: flex; gap: 8px; flex-wrap: wrap; }
    button { border: 1px solid var(--border); background: #0b1220; color: var(--text); padding: 10px 12px; border-radius: 8px; cursor: pointer; }
    button.primary { background: var(--accent); color: #041309; border-color: var(--accent-600); }
    button:disabled { opacity: .6; cursor: not-allowed; }
    .toast { position: fixed; right: 16px; bottom: 16px; background: #0b1220; color: var(--text); border: 1px solid var(--border);
      padding: 12px 14px; border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,.3); font-size: 14px; display: none; }
    .toast.show { display: block; }
    footer { font-size: 12px; color: var(--muted); text-align: center; margin-top: 4px; }
  </style>
</head>
<body>
  <main class="container" role="main" aria-label="Simple TCP File Transfer">
    <header>
      <h1>Simple TCP File Transfer</h1>
      <p>Drag a file below and send it over a real TCP socket to the receiver.</p>
    </header>

    <section class="grid grid-2" aria-label="Connection Settings">
      <div>
        <label for="server-ip">Server IP</label>
        <input id="server-ip" type="text" placeholder="e.g. 127.0.0.1" value="127.0.0.1"/>
      </div>
      <div>
        <label for="server-port">Server Port</label>
        <input id="server-port" type="number" min="1" max="65535" value="5001"/>
      </div>
    </section>

    <section id="dropzone" class="dropzone" tabindex="0" aria-label="File Dropzone" role="button">
      <div id="dz-text">
        <strong>Drop a file here</strong><br/>
        <span class="hint">or click to choose</span>
      </div>
      <div id="file-info" class="file-info" style="display:none;"></div>
      <input id="file-input" type="file" style="display:none;" />
    </section>

    <section class="progress-wrap" aria-label="Progress">
      <div class="stats">
        <div><span id="status">Idle</span></div>
        <div><span id="percent">0%</span></div>
      </div>
      <div class="bar" aria-label="Progress Bar" aria-valuemin="0" aria-valuemax="100">
        <span id="bar"></span>
      </div>
      <div class="stats">
        <div>Sent: <span id="sent-bytes">0</span></div>
        <div>Total: <span id="total-bytes">0</span></div>
      </div>
    </section>

    <section class="buttons">
      <button id="send" class="primary" disabled>Send</button>
      <button id="pause" disabled>Pause</button>
      <button id="resume" disabled>Resume</button>
      <button id="cancel" disabled>Cancel</button>
      <button id="reset">Reset</button>
    </section>

    <footer>Pure Python servers, simple UI. Educational and robust (no streaming body).</footer>
  </main>

  <div id="toast" class="toast" role="status" aria-live="polite"></div>

  <script>
  // Utility: format bytes nicely
  function fmtBytes(n) {
    const u = ['B','KB','MB','GB','TB'];
    let i = 0, x = n;
    while (x >= 1024 && i < u.length - 1) { x /= 1024; i++; }
    return x.toFixed(i ? 2 : 0) + ' ' + u[i];
  }
  const toast = document.getElementById('toast');
  function showToast(msg, ms=3000) {
    toast.textContent = msg; toast.classList.add('show'); setTimeout(() => toast.classList.remove('show'), ms);
  }

  // DOM
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const fileInfo = document.getElementById('file-info');
  const dzText = document.getElementById('dz-text');
  const serverIp = document.getElementById('server-ip');
  const serverPort = document.getElementById('server-port');
  const sendBtn = document.getElementById('send');
  const pauseBtn = document.getElementById('pause');
  const resumeBtn = document.getElementById('resume');
  const cancelBtn = document.getElementById('cancel');
  const resetBtn = document.getElementById('reset');
  const statusEl = document.getElementById('status');
  const percentEl = document.getElementById('percent');
  const barEl = document.getElementById('bar');
  const sentBytesEl = document.getElementById('sent-bytes');
  const totalBytesEl = document.getElementById('total-bytes');

  // App state
  let currentFile = null;
  let paused = false;
  let canceled = false;
  let sessionId = null;
  let bytesSent = 0;
  let totalBytes = 0;
  const CHUNK_SIZE = 256 * 1024; // 256 KB per request for smooth progress

  // Validation
  const MAX_SIZE = 2 * 1024 * 1024 * 1024; // 2GB
  const BLOCKED_EXT = [];

  function setStatus(text) { statusEl.textContent = text; }
  function setProgress(n, total) {
    const pct = total ? ((n / total) * 100) : 0;
    percentEl.textContent = pct.toFixed(1) + '%';
    barEl.style.width = Math.min(100, pct).toFixed(2) + '%';
    sentBytesEl.textContent = fmtBytes(n);
  }
  function setTotal(n) { totalBytesEl.textContent = fmtBytes(n); }
  function resetProgress() {
    setStatus('Idle'); setProgress(0, 1); sentBytesEl.textContent = '0'; totalBytesEl.textContent = '0'; barEl.style.width = '0%';
  }

  function selectFile(file) {
    if (!file) return;
    if (file.size <= 0) { showToast('Empty file is not allowed.'); return; }
    if (file.size > MAX_SIZE) { showToast('File too large (limit 2GB for demo).'); return; }
    const name = file.name || 'unnamed';
    const ext = name.includes('.') ? name.slice(name.lastIndexOf('.')).toLowerCase() : '';
    if (BLOCKED_EXT.includes(ext)) { showToast('This file type is blocked for demo.'); return; }

    currentFile = file; totalBytes = file.size; bytesSent = 0;
    fileInfo.style.display = 'block'; fileInfo.textContent = `${name} — ${fmtBytes(file.size)}`;
    dzText.style.display = 'none'; sendBtn.disabled = false; setTotal(file.size); resetProgress();
  }

  // Drag & drop
  dropzone.addEventListener('click', () => fileInput.click());
  dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', (e) => { e.preventDefault(); dropzone.classList.remove('dragover');
    const f = e.dataTransfer.files && e.dataTransfer.files[0]; selectFile(f); });
  fileInput.addEventListener('change', (e) => { const f = e.target.files && e.target.files[0]; selectFile(f); });

  async function beginSession(ip, port) {
    const res = await fetch(`/begin?host=${encodeURIComponent(ip)}&port=${encodeURIComponent(port)}`, {
      method: 'POST',
      headers: {
        'X-Filename': encodeURIComponent(currentFile.name || 'unnamed'),
        'X-Filesize': String(currentFile.size)
      }
    });
    const data = await res.json();
    if (!res.ok || data.status !== 'OK') throw new Error(data.message || `HTTP ${res.status}`);
    return data;
  }
  async function sendChunk(id, blob) {
    const res = await fetch(`/chunk?id=${encodeURIComponent(id)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/octet-stream' },
      body: blob
    });
    const data = await res.json();
    if (!res.ok || data.status !== 'OK') throw new Error(data.message || `HTTP ${res.status}`);
    return data;
  }
  async function endSession(id) {
    const res = await fetch(`/end?id=${encodeURIComponent(id)}`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || `HTTP ${res.status}`);
    return data;
  }
  async function cancelSession(id) {
    try { await fetch(`/cancel?id=${encodeURIComponent(id)}`, { method: 'POST' }); } catch(e) {}
  }

  async function sendFile() {
    if (!currentFile) { showToast('Please choose a file first.'); return; }
    const ip = (serverIp.value || '').trim();
    const port = parseInt(serverPort.value, 10);
    if (!ip || !(port > 0 && port <= 65535)) { showToast('Enter a valid Server IP and Port.'); return; }

    paused = false; canceled = false; sessionId = null; bytesSent = 0;
    sendBtn.disabled = true; pauseBtn.disabled = false; resumeBtn.disabled = true; cancelBtn.disabled = false;
    setStatus('Connecting...');

    try {
      const begin = await beginSession(ip, port);
      sessionId = begin.session_id;
      setStatus('Sending...');

      let offset = 0;
      while (offset < currentFile.size) {
        if (canceled) throw new Error('Canceled');
        if (paused) {
          setStatus('Paused');
          await new Promise(r => setTimeout(r, 100));
          continue;
        }
        const end = Math.min(offset + CHUNK_SIZE, currentFile.size);
        const chunk = currentFile.slice(offset, end);
        await sendChunk(sessionId, chunk);
        offset = end;
        bytesSent = offset;
        setStatus('Sending...');
        setProgress(bytesSent, totalBytes);
      }

      const done = await endSession(sessionId);
      setStatus('Completed'); setProgress(totalBytes, totalBytes);
      pauseBtn.disabled = true; resumeBtn.disabled = true; cancelBtn.disabled = true;
      showToast(`Success! Saved as: ${done.saved_as}`);

    } catch (err) {
      console.error(err);
      setStatus('Canceled or Failed');
      showToast(err.message || 'Transfer failed.');
      if (sessionId) { await cancelSession(sessionId); }
      sendBtn.disabled = false; pauseBtn.disabled = true; resumeBtn.disabled = true; cancelBtn.disabled = true;
    }
  }

  sendBtn.addEventListener('click', () => { resumeBtn.disabled = false; sendFile(); });
  pauseBtn.addEventListener('click', () => { paused = true; pauseBtn.disabled = true; resumeBtn.disabled = false; });
  resumeBtn.addEventListener('click', () => { paused = false; pauseBtn.disabled = false; resumeBtn.disabled = true; });
  cancelBtn.addEventListener('click', async () => { canceled = true; if (sessionId) await cancelSession(sessionId); });
  resetBtn.addEventListener('click', () => {
    currentFile = null; fileInput.value = '';
    fileInfo.style.display = 'none'; dzText.style.display = 'block';
    sendBtn.disabled = true; pauseBtn.disabled = true; resumeBtn.disabled = true; cancelBtn.disabled = true;
    resetProgress();
  });

  resetProgress();
  </script>
</body>
</html>
"""

# ------------- HTTP Handler -------------

class Handler(BaseHTTPRequestHandler):
    # Serve SPA
    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(INDEX_HTML.encode("utf-8"))
            return
        self.send_response(404)
        self.send_header("Connection", "close")
        self.end_headers()

    # Router for POST endpoints
    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/begin":
            return self.handle_begin(parsed)
        if parsed.path == "/chunk":
            return self.handle_chunk(parsed)
        if parsed.path == "/end":
            return self.handle_end(parsed)
        if parsed.path == "/cancel":
            return self.handle_cancel(parsed)
        self.send_json(404, {"status": "ERROR", "message": "Not found"})

    # --- Endpoint implementations ---

    def handle_begin(self, parsed):
        q = parse_qs(parsed.query)
        host = (q.get("host") or [""])[0]
        port_str = (q.get("port") or [""])[0]
        try:
            port = int(port_str)
        except Exception:
            return self.send_json(400, {"status": "ERROR", "message": "Invalid port"})
        if not host or not (1 <= port <= 65535):
            return self.send_json(400, {"status": "ERROR", "message": "Invalid host or port"})

        x_filename = self.headers.get("X-Filename") or ""
        x_filesize = self.headers.get("X-Filesize") or ""
        try:
            filename = unquote(x_filename)
        except Exception:
            filename = x_filename
        try:
            filesize = int(x_filesize)
        except Exception:
            filesize = -1
        if filesize <= 0:
            return self.send_json(400, {"status": "ERROR", "message": "Missing or invalid file size"})

        try:
            conn = socket.create_connection((host, port), timeout=10)
            # Send header to TCP server
            header = {"filename": filename, "filesize": filesize}
            body = json.dumps(header).encode("utf-8")
            conn.sendall(pack_length(len(body)))
            conn.sendall(body)

            # Await OK
            server_resp = self.recv_json(conn)
            if server_resp.get("status") != "OK":
                msg = server_resp.get("message", "Server rejected the upload")
                conn.close()
                return self.send_json(400, {"status": "ERROR", "message": msg})

            save_as = server_resp.get("save_as") or filename
            session_id = secrets.token_hex(16)
            with SESSIONS_LOCK:
                SESSIONS[session_id] = {
                    "conn": conn,
                    "filesize": filesize,
                    "received": 0,
                    "save_as": save_as,
                }
            return self.send_json(200, {"status": "OK", "session_id": session_id, "save_as": save_as})

        except Exception as e:
            return self.send_json(500, {"status": "ERROR", "message": str(e)})

    def handle_chunk(self, parsed):
        q = parse_qs(parsed.query)
        session_id = (q.get("id") or [""])[0]
        if not session_id:
            return self.send_json(400, {"status": "ERROR", "message": "Missing session id"})

        content_length = self.headers.get("Content-Length")
        try:
            n = int(content_length or "0")
        except Exception:
            return self.send_json(400, {"status": "ERROR", "message": "Missing Content-Length"})

        with SESSIONS_LOCK:
            sess = SESSIONS.get(session_id)
        if not sess:
            return self.send_json(404, {"status": "ERROR", "message": "Invalid session"})
        conn: socket.socket = sess["conn"]
        filesize = sess["filesize"]
        received = sess["received"]

        remaining_total = filesize - received
        if n > remaining_total:
            return self.send_json(400, {"status": "ERROR", "message": "Chunk exceeds remaining bytes"})

        try:
            to_forward = n
            while to_forward > 0:
                chunk = self.rfile.read(min(CHUNK_SIZE, to_forward))
                if not chunk:
                    raise ConnectionError("Unexpected EOF in chunk body")
                conn.sendall(chunk)
                to_forward -= len(chunk)

            # Update session counters
            with SESSIONS_LOCK:
                sess["received"] += n
                new_received = sess["received"]
            remaining = filesize - new_received

            # Log progress roughly each ~1MB
            if new_received % (1024 * 1024) < CHUNK_SIZE:
                pct = (new_received / filesize) * 100 if filesize else 100
                print(f"[HTTP->TCP] Forwarding: {new_received}/{filesize} bytes ({pct:.2f}%)")

            return self.send_json(200, {"status": "OK", "received": new_received, "remaining": remaining})

        except Exception as e:
            # On error, close and remove session to avoid dangling sockets
            try:
                conn.close()
            except Exception:
                pass
            with SESSIONS_LOCK:
                SESSIONS.pop(session_id, None)
            return self.send_json(500, {"status": "ERROR", "message": str(e)})

    def handle_end(self, parsed):
        q = parse_qs(parsed.query)
        session_id = (q.get("id") or [""])[0]
        if not session_id:
            return self.send_json(400, {"status": "ERROR", "message": "Missing session id"})

        with SESSIONS_LOCK:
            sess = SESSIONS.get(session_id)
        if not sess:
            return self.send_json(404, {"status": "ERROR", "message": "Invalid session"})

        conn: socket.socket = sess["conn"]
        filesize = sess["filesize"]
        received = sess["received"]

        if received != filesize:
            # Inform client but try to read any server error message
            try:
                resp = self.recv_json(conn)
            except Exception:
                resp = {"status": "ERROR", "message": "Size mismatch at end"}
            try:
                conn.close()
            except Exception:
                pass
            with SESSIONS_LOCK:
                SESSIONS.pop(session_id, None)
            return self.send_json(400, {"status": "ERROR", "message": resp.get("message", "Size mismatch")})

        try:
            # Await final DONE from TCP server
            final_resp = self.recv_json(conn)
            status_code = 200 if final_resp.get("status") == "DONE" else 500
            payload = {
                "status": final_resp.get("status", "ERROR"),
                "saved_as": final_resp.get("saved_as"),
                "bytes_received": final_resp.get("bytes_received"),
                "message": final_resp.get("message", "OK"),
                "renamed": final_resp.get("renamed", False),
            }
            return self.send_json(status_code, payload)
        except Exception as e:
            return self.send_json(500, {"status": "ERROR", "message": str(e)})
        finally:
            try:
                conn.close()
            except Exception:
                pass
            with SESSIONS_LOCK:
                SESSIONS.pop(session_id, None)

    def handle_cancel(self, parsed):
        q = parse_qs(parsed.query)
        session_id = (q.get("id") or [""])[0]
        if not session_id:
            return self.send_json(400, {"status": "ERROR", "message": "Missing session id"})
        with SESSIONS_LOCK:
            sess = SESSIONS.pop(session_id, None)
        if not sess:
            return self.send_json(200, {"status": "OK", "message": "No session"})
        try:
            sess["conn"].close()
        except Exception:
            pass
        return self.send_json(200, {"status": "OK", "message": "Canceled"})

    # --- Helpers ---

    def recv_json(self, conn: socket.socket):
        """Receive a framed JSON message (8-byte length + body) from TCP server."""
        length_bytes = self._recv_exactly(conn, HEADER_LEN_SIZE)
        length = unpack_length(length_bytes)
        body = self._recv_exactly(conn, length)
        return json.loads(body.decode("utf-8"))

    def _recv_exactly(self, conn: socket.socket, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = conn.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("TCP server closed connection early")
            buf += chunk
        return buf

    def send_json(self, status_code: int, data: dict):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)


def start_http_ui(host="127.0.0.1", port=8000):
    print(f"HTTP Front-End running at http://{host}:{port}")
    print("Open the URL in your browser. Press Ctrl+C to stop.")
    with ThreadingHTTPServer((host, port), Handler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    start_http_ui(host="127.0.0.1", port=8000)
