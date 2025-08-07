#!/usr/bin/env python3
"""
Complete File Transfer System with TCP Sockets
Author: AI Assistant
Description: A web-based file transfer application using Flask and TCP sockets
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import os
import socket
import threading
import time
import json
from datetime import datetime
import uuid
import sys

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'file-transfer-secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
UPLOAD_FOLDER = 'uploads'
RECEIVED_FOLDER = 'received'
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
RECEIVER_HOST = 'localhost'
RECEIVER_PORT = 9999
CHUNK_SIZE = 4096

# Global variables
active_transfers = {}
transfer_history = []
receiver_server = None

class FileReceiver:
    """TCP Socket Server for receiving files"""
    
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        
    def start_server(self):
        """Start the TCP receiver server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            log_message("info", f"TCP Receiver started on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    thread = threading.Thread(target=self.handle_client, args=(client_socket, address))
                    thread.daemon = True
                    thread.start()
                except Exception as e:
                    if self.running:
                        log_message("error", f"Server error: {str(e)}")
                    break
                    
        except Exception as e:
            log_message("error", f"Failed to start receiver server: {str(e)}")
            sys.exit(1)
    
    def handle_client(self, client_socket, address):
        """Handle incoming file transfer from client"""
        file_id = None
        try:
            # Receive file metadata
            metadata_size = int.from_bytes(client_socket.recv(4), byteorder='big')
            metadata_json = client_socket.recv(metadata_size).decode('utf-8')
            metadata = json.loads(metadata_json)
            
            file_id = metadata['file_id']
            filename = metadata['filename']
            file_size = metadata['file_size']
            
            log_message("info", f"Receiving: {filename} ({self.format_size(file_size)})")
            
            # Create safe filename (handle duplicates)
            safe_filename = self.get_safe_filename(filename)
            file_path = os.path.join(RECEIVED_FOLDER, safe_filename)
            
            # Update transfer status
            if file_id in active_transfers:
                active_transfers[file_id]['status'] = 'transferring'
                active_transfers[file_id]['received_filename'] = safe_filename
                socketio.emit('transfer_update', active_transfers[file_id])
            
            # Receive file data with progress tracking
            received_size = 0
            with open(file_path, 'wb') as f:
                while received_size < file_size:
                    remaining = file_size - received_size
                    chunk_size = min(CHUNK_SIZE, remaining)
                    chunk = client_socket.recv(chunk_size)
                    
                    if not chunk:
                        break
                        
                    f.write(chunk)
                    received_size += len(chunk)
                    
                    # Update progress
                    if file_id in active_transfers:
                        progress = (received_size / file_size) * 100
                        active_transfers[file_id]['progress'] = progress
                        active_transfers[file_id]['received_size'] = received_size
                        socketio.emit('transfer_update', active_transfers[file_id])
            
            # Send confirmation
            client_socket.send(b"TRANSFER_COMPLETE")
            
            # Update final status
            if file_id in active_transfers:
                active_transfers[file_id]['status'] = 'completed'
                active_transfers[file_id]['progress'] = 100
                active_transfers[file_id]['end_time'] = datetime.now().isoformat()
                socketio.emit('transfer_update', active_transfers[file_id])
                socketio.emit('transfer_complete', {
                    'file_id': file_id,
                    'filename': safe_filename,
                    'message': f'✅ {safe_filename} transferred successfully!'
                })
            
            log_message("success", f"Transfer completed: {safe_filename}")
            
        except Exception as e:
            log_message("error", f"Transfer failed: {str(e)}")
            if file_id and file_id in active_transfers:
                active_transfers[file_id]['status'] = 'error'
                active_transfers[file_id]['error'] = str(e)
                socketio.emit('transfer_update', active_transfers[file_id])
        finally:
            client_socket.close()
    
    def get_safe_filename(self, filename):
        """Generate safe filename, handling duplicates"""
        base_name, extension = os.path.splitext(filename)
        counter = 1
        safe_filename = filename
        
        while os.path.exists(os.path.join(RECEIVED_FOLDER, safe_filename)):
            safe_filename = f"{base_name}_{counter}{extension}"
            counter += 1
            
        if safe_filename != filename:
            log_message("warning", f"File renamed: {filename} → {safe_filename}")
            socketio.emit('file_renamed', {
                'original': filename,
                'renamed': safe_filename,
                'message': f'⚠️ File renamed to avoid duplicate: {safe_filename}'
            })
            
        return safe_filename
    
    def format_size(self, bytes):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.1f} TB"
    
    def stop_server(self):
        """Stop the TCP server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()

def send_file_via_tcp(file_path, filename, file_id):
    """Send file to TCP receiver server"""
    try:
        # Update status
        if file_id in active_transfers:
            active_transfers[file_id]['status'] = 'connecting'
            socketio.emit('transfer_update', active_transfers[file_id])
        
        # Connect to receiver
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(30)  # 30 second timeout
        client_socket.connect((RECEIVER_HOST, RECEIVER_PORT))
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Prepare metadata
        metadata = {
            'file_id': file_id,
            'filename': filename,
            'file_size': file_size
        }
        metadata_json = json.dumps(metadata).encode('utf-8')
        
        # Send metadata
        client_socket.send(len(metadata_json).to_bytes(4, byteorder='big'))
        client_socket.send(metadata_json)
        
        log_message("info", f"Sending: {filename}")
        
        # Send file data with progress tracking
        sent_size = 0
        start_time = time.time()
        
        with open(file_path, 'rb') as f:
            while sent_size < file_size:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                    
                client_socket.send(chunk)
                sent_size += len(chunk)
                
                # Calculate transfer speed
                elapsed_time = time.time() - start_time
                if elapsed_time > 0:
                    speed = sent_size / elapsed_time
                    remaining_bytes = file_size - sent_size
                    eta = remaining_bytes / speed if speed > 0 else 0
                else:
                    speed = 0
                    eta = 0
                
                # Update progress
                if file_id in active_transfers:
                    progress = (sent_size / file_size) * 100
                    active_transfers[file_id]['progress'] = progress
                    active_transfers[file_id]['sent_size'] = sent_size
                    active_transfers[file_id]['speed'] = f"{speed / 1024:.1f} KB/s" if speed > 0 else "0 KB/s"
                    active_transfers[file_id]['eta'] = f"{eta:.0f}s" if eta > 0 else "0s"
                    socketio.emit('transfer_update', active_transfers[file_id])
                
                # Small delay for smooth progress updates
                time.sleep(0.01)
        
        # Wait for confirmation
        response = client_socket.recv(1024)
        client_socket.close()
        
        if response == b"TRANSFER_COMPLETE":
            log_message("success", f"Send completed: {filename}")
        else:
            raise Exception("Transfer confirmation failed")
            
    except Exception as e:
        log_message("error", f"Send failed for {filename}: {str(e)}")
        if file_id in active_transfers:
            active_transfers[file_id]['status'] = 'error'
            active_transfers[file_id]['error'] = str(e)
            socketio.emit('transfer_update', active_transfers[file_id])

def log_message(level, message):
    """Add message to transfer log"""
    log_entry = {
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'level': level,
        'message': message
    }
    transfer_history.append(log_entry)
    
    # Keep only last 100 log entries
    if len(transfer_history) > 100:
        transfer_history.pop(0)
    
    socketio.emit('log_message', log_entry)
    print(f"[{log_entry['timestamp']}] {level.upper()}: {message}")

def validate_file(file):
    """Validate uploaded file"""
    errors = []
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    if file_size > MAX_FILE_SIZE:
        errors.append(f"File exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit ({file_size // (1024*1024)}MB)")
    
    if file_size == 0:
        errors.append("File is empty")
    
    # Check filename
    if not file.filename:
        errors.append("No filename provided")
    elif len(file.filename) > 255:
        errors.append("Filename too long (max 255 characters)")
    elif any(char in file.filename for char in '<>:"/\\|?*'):
        errors.append("Filename contains invalid characters")
    
    return errors

def setup_directories():
    """Create necessary directories"""
    directories = [UPLOAD_FOLDER, RECEIVED_FOLDER]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Flask Routes
@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('.', 'index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file upload"""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    results = []
    
    for file in files:
        if file.filename == '':
            continue
            
        # Validate file
        validation_errors = validate_file(file)
        if validation_errors:
            results.append({
                'filename': file.filename,
                'status': 'error',
                'errors': validation_errors
            })
            log_message("error", f"Validation failed for {file.filename}: {', '.join(validation_errors)}")
            continue
        
        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            
            # Save uploaded file
            filename = file.filename
            file_path = os.path.join(UPLOAD_FOLDER, f"{file_id}_{filename}")
            file.save(file_path)
            
            file_size = os.path.getsize(file_path)
            
            # Create transfer record
            transfer_record = {
                'file_id': file_id,
                'filename': filename,
                'file_path': file_path,
                'file_size': file_size,
                'status': 'pending',
                'progress': 0,
                'start_time': datetime.now().isoformat(),
                'sent_size': 0,
                'received_size': 0,
                'speed': '0 KB/s',
                'eta': '0s'
            }
            
            active_transfers[file_id] = transfer_record
            
            results.append({
                'file_id': file_id,
                'filename': filename,
                'status': 'uploaded',
                'size': file_size
            })
            
            log_message("info", f"File uploaded: {filename} ({file_size} bytes)")
            
        except Exception as e:
            results.append({
                'filename': file.filename,
                'status': 'error',
                'errors': [str(e)]
            })
            log_message("error", f"Upload failed for {file.filename}: {str(e)}")
    
    return jsonify({'results': results})

@app.route('/start_transfer/<file_id>', methods=['POST'])
def start_transfer(file_id):
    """Start file transfer"""
    if file_id not in active_transfers:
        return jsonify({'error': 'File not found'}), 404
    
    transfer = active_transfers[file_id]
    
    if transfer['status'] in ['transferring', 'completed']:
        return jsonify({'error': 'Transfer already in progress or completed'}), 400
    
    # Start transfer in background thread
    thread = threading.Thread(
        target=send_file_via_tcp,
        args=(transfer['file_path'], transfer['filename'], file_id)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Transfer started'})

@app.route('/pause_transfer/<file_id>', methods=['POST'])
def pause_transfer(file_id):
    """Pause file transfer (simplified implementation)"""
    if file_id not in active_transfers:
        return jsonify({'error': 'File not found'}), 404
    
    active_transfers[file_id]['status'] = 'paused'
    socketio.emit('transfer_update', active_transfers[file_id])
    log_message("warning", f"Transfer paused: {active_transfers[file_id]['filename']}")
    
    return jsonify({'message': 'Transfer paused'})

@app.route('/resume_transfer/<file_id>', methods=['POST'])
def resume_transfer(file_id):
    """Resume file transfer"""
    if file_id not in active_transfers:
        return jsonify({'error': 'File not found'}), 404
    
    return start_transfer(file_id)

@app.route('/remove_transfer/<file_id>', methods=['DELETE'])
def remove_transfer(file_id):
    """Remove file transfer"""
    if file_id not in active_transfers:
        return jsonify({'error': 'File not found'}), 404
    
    transfer = active_transfers[file_id]
    
    # Remove uploaded file
    if os.path.exists(transfer['file_path']):
        os.remove(transfer['file_path'])
    
    # Remove from active transfers
    del active_transfers[file_id]
    
    log_message("info", f"Transfer removed: {transfer['filename']}")
    
    return jsonify({'message': 'Transfer removed'})

@app.route('/status')
def get_status():
    """Get system status"""
    return jsonify({
        'active_transfers': len(active_transfers),
        'total_logs': len(transfer_history),
        'server_running': receiver_server.running if receiver_server else False
    })

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'message': 'Connected to File Transfer System'})
    emit('transfers_update', list(active_transfers.values()))
    emit('logs_update', transfer_history)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

def initialize_system():
    """Initialize the file transfer system"""
    global receiver_server
    
    print("🚀 Initializing File Transfer System...")
    
    # Setup directories
    setup_directories()
    print("✅ Directories created")
    
    # Start TCP receiver server
    receiver_server = FileReceiver(RECEIVER_HOST, RECEIVER_PORT)
    receiver_thread = threading.Thread(target=receiver_server.start_server)
    receiver_thread.daemon = True
    receiver_thread.start()
    
    # Wait a moment for server to start
    time.sleep(1)
    
    log_message("info", "File Transfer System initialized")
    log_message("info", f"Web interface: http://localhost:5000")
    log_message("info", f"TCP receiver: {RECEIVER_HOST}:{RECEIVER_PORT}")
    
    print("✅ System ready!")

if __name__ == '__main__':
    try:
        initialize_system()
        print("\n" + "="*60)
        print("🌐 Starting web server on http://localhost:5000")
        print("📁 Upload folder: ./uploads")
        print("📥 Received folder: ./received")
        print("🔌 TCP receiver: localhost:9999")
        print("="*60)
        print("\n💡 Open http://localhost:5000 in your browser")
        print("⏹️  Press Ctrl+C to stop\n")
        
        socketio.run(app, debug=False, host='0.0.0.0', port=5000)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down File Transfer System...")
        if receiver_server:
            receiver_server.stop_server()
        print("👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error starting system: {e}")
        sys.exit(1)
