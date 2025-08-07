from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import os
import socket
import threading
import time
import hashlib
import json
from datetime import datetime
import uuid

# Initialize Flask app without template folder
app = Flask(__name__, static_folder='static', static_url_path='')
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
UPLOAD_FOLDER = 'uploads'
RECEIVED_FOLDER = 'received'
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
RECEIVER_HOST = 'localhost'
RECEIVER_PORT = 9999
CHUNK_SIZE = 4096

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RECEIVED_FOLDER, exist_ok=True)

# Global variables for tracking transfers
active_transfers = {}
transfer_history = []

class FileReceiver:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        
    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        
        log_message("info", f"Receiver server started on {self.host}:{self.port}")
        
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
    
    def handle_client(self, client_socket, address):
        try:
            # Receive file metadata
            metadata_size = int.from_bytes(client_socket.recv(4), byteorder='big')
            metadata_json = client_socket.recv(metadata_size).decode('utf-8')
            metadata = json.loads(metadata_json)
            
            file_id = metadata['file_id']
            filename = metadata['filename']
            file_size = metadata['file_size']
            
            log_message("info", f"Receiving file: {filename} ({file_size} bytes)")
            
            # Create safe filename
            safe_filename = self.get_safe_filename(filename)
            file_path = os.path.join(RECEIVED_FOLDER, safe_filename)
            
            # Update transfer status
            if file_id in active_transfers:
                active_transfers[file_id]['status'] = 'transferring'
                active_transfers[file_id]['received_filename'] = safe_filename
                socketio.emit('transfer_update', active_transfers[file_id])
            
            # Receive file data
            received_size = 0
            with open(file_path, 'wb') as f:
                while received_size < file_size:
                    chunk = client_socket.recv(min(CHUNK_SIZE, file_size - received_size))
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
            client_socket.send(b"OK")
            
            # Update final status
            if file_id in active_transfers:
                active_transfers[file_id]['status'] = 'completed'
                active_transfers[file_id]['progress'] = 100
                active_transfers[file_id]['end_time'] = datetime.now().isoformat()
                socketio.emit('transfer_update', active_transfers[file_id])
                socketio.emit('transfer_complete', {
                    'file_id': file_id,
                    'filename': safe_filename,
                    'message': f'File {safe_filename} transferred successfully!'
                })
            
            log_message("success", f"File received successfully: {safe_filename}")
            
        except Exception as e:
            log_message("error", f"Error receiving file: {str(e)}")
            if file_id in active_transfers:
                active_transfers[file_id]['status'] = 'error'
                active_transfers[file_id]['error'] = str(e)
                socketio.emit('transfer_update', active_transfers[file_id])
        finally:
            client_socket.close()
    
    def get_safe_filename(self, filename):
        # Handle duplicate filenames
        base_name, extension = os.path.splitext(filename)
        counter = 1
        safe_filename = filename
        
        while os.path.exists(os.path.join(RECEIVED_FOLDER, safe_filename)):
            safe_filename = f"{base_name}_{counter}{extension}"
            counter += 1
            
        if safe_filename != filename:
            log_message("warning", f"File renamed to avoid duplicate: {filename} -> {safe_filename}")
            
        return safe_filename
    
    def stop_server(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()

def send_file(file_path, filename, file_id):
    try:
        # Update status
        if file_id in active_transfers:
            active_transfers[file_id]['status'] = 'connecting'
            socketio.emit('transfer_update', active_transfers[file_id])
        
        # Connect to receiver
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
        
        # Send metadata size and metadata
        client_socket.send(len(metadata_json).to_bytes(4, byteorder='big'))
        client_socket.send(metadata_json)
        
        log_message("info", f"Sending file: {filename}")
        
        # Send file data
        sent_size = 0
        with open(file_path, 'rb') as f:
            while sent_size < file_size:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                client_socket.send(chunk)
                sent_size += len(chunk)
                
                # Update progress
                if file_id in active_transfers:
                    progress = (sent_size / file_size) * 100
                    active_transfers[file_id]['progress'] = progress
                    active_transfers[file_id]['sent_size'] = sent_size
                    socketio.emit('transfer_update', active_transfers[file_id])
                
                # Small delay to make progress visible
                time.sleep(0.01)
        
        # Wait for confirmation
        response = client_socket.recv(1024)
        client_socket.close()
        
        if response == b"OK":
            log_message("success", f"File sent successfully: {filename}")
        else:
            raise Exception("Transfer confirmation failed")
            
    except Exception as e:
        log_message("error", f"Error sending file {filename}: {str(e)}")
        if file_id in active_transfers:
            active_transfers[file_id]['status'] = 'error'
            active_transfers[file_id]['error'] = str(e)
            socketio.emit('transfer_update', active_transfers[file_id])

def log_message(level, message):
    log_entry = {
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'level': level,
        'message': message
    }
    transfer_history.append(log_entry)
    socketio.emit('log_message', log_entry)
    print(f"[{log_entry['timestamp']}] {level.upper()}: {message}")

def validate_file(file):
    errors = []
    
    # Check file size
    if hasattr(file, 'content_length') and file.content_length > MAX_FILE_SIZE:
        errors.append(f"File size exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit")
    
    # Check filename
    if not file.filename:
        errors.append("No filename provided")
    elif not file.filename.replace('.', '').replace('_', '').replace('-', '').isalnum():
        # Allow only alphanumeric characters, dots, underscores, and hyphens
        errors.append("Filename contains invalid characters")
    
    return errors

# Initialize receiver server
receiver = FileReceiver(RECEIVER_HOST, RECEIVER_PORT)
receiver_thread = threading.Thread(target=receiver.start_server)
receiver_thread.daemon = True
receiver_thread.start()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
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
            continue
        
        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            
            # Save uploaded file
            filename = file.filename
            file_path = os.path.join(UPLOAD_FOLDER, f"{file_id}_{filename}")
            file.save(file_path)
            
            # Create transfer record
            transfer_record = {
                'file_id': file_id,
                'filename': filename,
                'file_path': file_path,
                'file_size': os.path.getsize(file_path),
                'status': 'pending',
                'progress': 0,
                'start_time': datetime.now().isoformat(),
                'sent_size': 0,
                'received_size': 0
            }
            
            active_transfers[file_id] = transfer_record
            
            results.append({
                'file_id': file_id,
                'filename': filename,
                'status': 'uploaded',
                'size': transfer_record['file_size']
            })
            
            log_message("info", f"File uploaded: {filename}")
            
        except Exception as e:
            results.append({
                'filename': file.filename,
                'status': 'error',
                'errors': [str(e)]
            })
    
    return jsonify({'results': results})

@app.route('/start_transfer/<file_id>', methods=['POST'])
def start_transfer(file_id):
    if file_id not in active_transfers:
        return jsonify({'error': 'File not found'}), 404
    
    transfer = active_transfers[file_id]
    
    if transfer['status'] in ['transferring', 'completed']:
        return jsonify({'error': 'Transfer already in progress or completed'}), 400
    
    # Start transfer in background thread
    thread = threading.Thread(
        target=send_file,
        args=(transfer['file_path'], transfer['filename'], file_id)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Transfer started'})

@app.route('/pause_transfer/<file_id>', methods=['POST'])
def pause_transfer(file_id):
    if file_id not in active_transfers:
        return jsonify({'error': 'File not found'}), 404
    
    # Note: In a real implementation, you'd need to implement pause/resume logic
    # This is a simplified version
    active_transfers[file_id]['status'] = 'paused'
    socketio.emit('transfer_update', active_transfers[file_id])
    log_message("warning", f"Transfer paused: {active_transfers[file_id]['filename']}")
    
    return jsonify({'message': 'Transfer paused'})

@app.route('/resume_transfer/<file_id>', methods=['POST'])
def resume_transfer(file_id):
    if file_id not in active_transfers:
        return jsonify({'error': 'File not found'}), 404
    
    # Resume transfer (simplified - in reality you'd resume from where it left off)
    return start_transfer(file_id)

@app.route('/remove_transfer/<file_id>', methods=['DELETE'])
def remove_transfer(file_id):
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

@app.route('/transfers')
def get_transfers():
    return jsonify(list(active_transfers.values()))

@app.route('/logs')
def get_logs():
    return jsonify(transfer_history)

@socketio.on('connect')
def handle_connect():
    emit('connected', {'message': 'Connected to file transfer system'})
    # Send current transfers and logs
    emit('transfers_update', list(active_transfers.values()))
    emit('logs_update', transfer_history)

if __name__ == '__main__':
    log_message("info", "File Transfer System starting...")
    log_message("info", f"Receiver server: {RECEIVER_HOST}:{RECEIVER_PORT}")
    log_message("info", "Web interface: http://localhost:5000")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
