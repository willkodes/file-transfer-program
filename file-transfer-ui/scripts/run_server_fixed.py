#!/usr/bin/env python3
"""
File Transfer System - TCP Socket Implementation (Fixed Version)
Run this script to start the complete file transfer system
"""

import os
import sys
import subprocess
import threading
import time

def install_requirements():
    """Install required packages"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Flask==2.3.3", "Flask-SocketIO==5.3.6"])
        print("✓ Requirements installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install requirements: {e}")
        sys.exit(1)

def create_directories():
    """Create necessary directories"""
    directories = ['uploads', 'received', 'static']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Directory created: {directory}")

def create_html_file():
    """Create the HTML file in the correct location"""
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Transfer System</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f8fafc;
            color: #334155;
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        .header {
            text-align: center;
            margin-bottom: 2rem;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 0.5rem;
        }

        .header p {
            color: #64748b;
            font-size: 1.1rem;
        }

        .main-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 2rem;
            margin-bottom: 2rem;
        }

        .card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            border: 1px solid #e2e8f0;
            overflow: hidden;
        }

        .card-header {
            padding: 1.5rem;
            border-bottom: 1px solid #e2e8f0;
        }

        .card-header h2 {
            font-size: 1.25rem;
            font-weight: 600;
            color: #1e293b;
        }

        .card-content {
            padding: 1.5rem;
        }

        /* Upload Area */
        .upload-area {
            border: 2px dashed #cbd5e1;
            border-radius: 8px;
            padding: 3rem;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
        }

        .upload-area:hover,
        .upload-area.drag-over {
            border-color: #3b82f6;
            background-color: #eff6ff;
        }

        .upload-icon {
            width: 48px;
            height: 48px;
            margin: 0 auto 1rem;
            color: #94a3b8;
        }

        .upload-text {
            font-size: 1.125rem;
            font-weight: 500;
            color: #475569;
            margin-bottom: 0.5rem;
        }

        .upload-subtext {
            color: #64748b;
            margin-bottom: 1rem;
        }

        .upload-button {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 6px;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
        }

        .upload-button:hover {
            background: #2563eb;
        }

        /* File List */
        .file-item {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }

        .file-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }

        .file-info {
            flex: 1;
        }

        .file-name {
            font-weight: 500;
            color: #1e293b;
            margin-bottom: 0.25rem;
        }

        .file-size {
            color: #64748b;
            font-size: 0.875rem;
        }

        .file-controls {
            display: flex;
            gap: 0.5rem;
        }

        .btn {
            padding: 0.5rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 0.875rem;
        }

        .btn-start {
            background: #10b981;
            color: white;
        }

        .btn-start:hover {
            background: #059669;
        }

        .btn-pause {
            background: #f59e0b;
            color: white;
        }

        .btn-pause:hover {
            background: #d97706;
        }

        .btn-remove {
            background: #ef4444;
            color: white;
        }

        .btn-remove:hover {
            background: #dc2626;
        }

        /* Progress Bar */
        .progress-container {
            margin-top: 0.75rem;
        }

        .progress-info {
            display: flex;
            justify-content: space-between;
            font-size: 0.875rem;
            color: #64748b;
            margin-bottom: 0.25rem;
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: #3b82f6;
            transition: width 0.3s ease;
        }

        .progress-fill.completed {
            background: #10b981;
        }

        .progress-fill.error {
            background: #ef4444;
        }

        .progress-fill.paused {
            background: #f59e0b;
        }

        /* Status */
        .status {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
            text-transform: uppercase;
        }

        .status-pending {
            background: #f1f5f9;
            color: #64748b;
        }

        .status-transferring {
            background: #dbeafe;
            color: #1d4ed8;
        }

        .status-completed {
            background: #d1fae5;
            color: #065f46;
        }

        .status-error {
            background: #fee2e2;
            color: #991b1b;
        }

        .status-paused {
            background: #fef3c7;
            color: #92400e;
        }

        /* Log Area */
        .log-container {
            background: #1e293b;
            border-radius: 8px;
            height: 400px;
            overflow: hidden;
        }

        .log-header {
            display: flex;
            align-items: center;
            padding: 1rem;
            background: #334155;
            gap: 0.5rem;
        }

        .log-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }

        .log-dot.red {
            background: #ef4444;
        }

        .log-dot.yellow {
            background: #f59e0b;
        }

        .log-dot.green {
            background: #10b981;
        }

        .log-title {
            color: #94a3b8;
            font-size: 0.875rem;
            margin-left: 0.5rem;
        }

        .log-content {
            padding: 1rem;
            height: calc(100% - 60px);
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.875rem;
            line-height: 1.4;
        }

        .log-entry {
            margin-bottom: 0.25rem;
        }

        .log-timestamp {
            color: #64748b;
        }

        .log-message {
            margin-left: 0.5rem;
        }

        .log-info {
            color: #94a3b8;
        }

        .log-success {
            color: #34d399;
        }

        .log-error {
            color: #f87171;
        }

        .log-warning {
            color: #fbbf24;
        }

        /* Notifications */
        .notification {
            position: fixed;
            top: 2rem;
            right: 2rem;
            background: white;
            border-radius: 8px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
            border-left: 4px solid #10b981;
            padding: 1rem;
            max-width: 400px;
            z-index: 1000;
            animation: slideIn 0.3s ease;
        }

        .notification.error {
            border-left-color: #ef4444;
        }

        .notification.warning {
            border-left-color: #f59e0b;
        }

        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        .hidden {
            display: none;
        }

        #fileInput {
            display: none;
        }

        @media (max-width: 1024px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>File Transfer System</h1>
            <p>TCP Socket-based file transfer with real-time progress tracking</p>
        </div>

        <div class="main-grid">
            <div class="left-panel">
                <!-- Upload Area -->
                <div class="card">
                    <div class="card-header">
                        <h2>Upload Files</h2>
                    </div>
                    <div class="card-content">
                        <div class="upload-area" id="uploadArea">
                            <svg class="upload-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                            </svg>
                            <div class="upload-text">Drop files here or click to browse</div>
                            <div class="upload-subtext">Supports all file types up to 100MB</div>
                            <button class="upload-button" onclick="document.getElementById('fileInput').click()">
                                Choose Files
                            </button>
                        </div>
                        <input type="file" id="fileInput" multiple>
                    </div>
                </div>

                <!-- File List -->
                <div class="card" style="margin-top: 2rem;">
                    <div class="card-header">
                        <h2>File Transfers</h2>
                    </div>
                    <div class="card-content">
                        <div id="fileList">
                            <div style="text-align: center; color: #64748b; padding: 2rem;">
                                No files uploaded yet
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="right-panel">
                <!-- Log Area -->
                <div class="card">
                    <div class="card-header">
                        <h2>Transfer Log</h2>
                    </div>
                    <div class="card-content" style="padding: 0;">
                        <div class="log-container">
                            <div class="log-header">
                                <div class="log-dot red"></div>
                                <div class="log-dot yellow"></div>
                                <div class="log-dot green"></div>
                                <div class="log-title">System Console</div>
                            </div>
                            <div class="log-content" id="logContent">
                                <!-- Log entries will be added here -->
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Initialize Socket.IO
        const socket = io();
        
        // Global variables
        let transfers = {};
        
        // DOM elements
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const fileList = document.getElementById('fileList');
        const logContent = document.getElementById('logContent');
        
        // Socket event handlers
        socket.on('connect', function() {
            console.log('Connected to server');
        });
        
        socket.on('transfer_update', function(transfer) {
            transfers[transfer.file_id] = transfer;
            updateFileList();
        });
        
        socket.on('transfer_complete', function(data) {
            showNotification('success', data.message);
        });
        
        socket.on('log_message', function(log) {
            addLogEntry(log);
        });
        
        socket.on('transfers_update', function(transferList) {
            transfers = {};
            transferList.forEach(transfer => {
                transfers[transfer.file_id] = transfer;
            });
            updateFileList();
        });
        
        socket.on('logs_update', function(logs) {
            logContent.innerHTML = '';
            logs.forEach(log => {
                addLogEntry(log);
            });
        });
        
        // File upload handling
        uploadArea.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', handleDragOver);
        uploadArea.addEventListener('dragleave', handleDragLeave);
        uploadArea.addEventListener('drop', handleDrop);
        fileInput.addEventListener('change', handleFileSelect);
        
        function handleDragOver(e) {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        }
        
        function handleDragLeave(e) {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
        }
        
        function handleDrop(e) {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            const files = e.dataTransfer.files;
            uploadFiles(files);
        }
        
        function handleFileSelect(e) {
            const files = e.target.files;
            uploadFiles(files);
        }
        
        function uploadFiles(files) {
            const formData = new FormData();
            
            for (let file of files) {
                formData.append('files', file);
            }
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                data.results.forEach(result => {
                    if (result.status === 'uploaded') {
                        // File uploaded successfully, add to transfers
                        transfers[result.file_id] = {
                            file_id: result.file_id,
                            filename: result.filename,
                            file_size: result.size,
                            status: 'pending',
                            progress: 0
                        };
                    } else if (result.status === 'error') {
                        // Show validation errors
                        result.errors.forEach(error => {
                            showNotification('error', `${result.filename}: ${error}`);
                        });
                    }
                });
                updateFileList();
            })
            .catch(error => {
                console.error('Upload error:', error);
                showNotification('error', 'Upload failed');
            });
        }
        
        function updateFileList() {
            const transferList = Object.values(transfers);
            
            if (transferList.length === 0) {
                fileList.innerHTML = '<div style="text-align: center; color: #64748b; padding: 2rem;">No files uploaded yet</div>';
                return;
            }
            
            fileList.innerHTML = transferList.map(transfer => `
                <div class="file-item">
                    <div class="file-header">
                        <div class="file-info">
                            <div class="file-name">${transfer.filename}</div>
                            <div class="file-size">${formatFileSize(transfer.file_size)}</div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 1rem;">
                            <span class="status status-${transfer.status}">${transfer.status}</span>
                            <div class="file-controls">
                                ${getControlButtons(transfer)}
                            </div>
                        </div>
                    </div>
                    <div class="progress-container">
                        <div class="progress-info">
                            <span>${transfer.progress.toFixed(1)}%</span>
                            <span>${getProgressInfo(transfer)}</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill ${transfer.status}" style="width: ${transfer.progress}%"></div>
                        </div>
                    </div>
                </div>
            `).join('');
        }
        
        function getControlButtons(transfer) {
            let buttons = '';
            
            if (transfer.status === 'pending' || transfer.status === 'paused') {
                buttons += `<button class="btn btn-start" onclick="startTransfer('${transfer.file_id}')">▶</button>`;
            }
            
            if (transfer.status === 'transferring') {
                buttons += `<button class="btn btn-pause" onclick="pauseTransfer('${transfer.file_id}')">⏸</button>`;
            }
            
            if (transfer.status !== 'transferring') {
                buttons += `<button class="btn btn-remove" onclick="removeTransfer('${transfer.file_id}')">✕</button>`;
            }
            
            return buttons;
        }
        
        function getProgressInfo(transfer) {
            if (transfer.status === 'completed') {
                return 'Completed';
            } else if (transfer.status === 'transferring' && transfer.sent_size) {
                return `${formatFileSize(transfer.sent_size)} sent`;
            }
            return '';
        }
        
        function startTransfer(fileId) {
            fetch(`/start_transfer/${fileId}`, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        showNotification('error', data.error);
                    }
                })
                .catch(error => {
                    console.error('Start transfer error:', error);
                    showNotification('error', 'Failed to start transfer');
                });
        }
        
        function pauseTransfer(fileId) {
            fetch(`/pause_transfer/${fileId}`, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        showNotification('error', data.error);
                    }
                })
                .catch(error => {
                    console.error('Pause transfer error:', error);
                    showNotification('error', 'Failed to pause transfer');
                });
        }
        
        function removeTransfer(fileId) {
            if (confirm('Are you sure you want to remove this transfer?')) {
                fetch(`/remove_transfer/${fileId}`, { method: 'DELETE' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            showNotification('error', data.error);
                        } else {
                            delete transfers[fileId];
                            updateFileList();
                        }
                    })
                    .catch(error => {
                        console.error('Remove transfer error:', error);
                        showNotification('error', 'Failed to remove transfer');
                    });
            }
        }
        
        function addLogEntry(log) {
            const logEntry = document.createElement('div');
            logEntry.className = 'log-entry';
            logEntry.innerHTML = `
                <span class="log-timestamp">[${log.timestamp}]</span>
                <span class="log-message log-${log.level}">${log.message}</span>
            `;
            logContent.appendChild(logEntry);
            logContent.scrollTop = logContent.scrollHeight;
        }
        
        function showNotification(type, message) {
            const notification = document.createElement('div');
            notification.className = `notification ${type}`;
            notification.innerHTML = `
                <div style="font-weight: 500; margin-bottom: 0.25rem;">
                    ${type === 'success' ? '✓' : type === 'error' ? '✗' : '⚠'} 
                    ${type.charAt(0).toUpperCase() + type.slice(1)}
                </div>
                <div>${message}</div>
            `;
            
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.remove();
            }, 5000);
        }
        
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
    </script>
</body>
</html>'''
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("✓ HTML file created: index.html")

def main():
    print("=" * 60)
    print("FILE TRANSFER SYSTEM - FIXED VERSION")
    print("=" * 60)
    
    # Install requirements
    print("\n1. Installing requirements...")
    install_requirements()
    
    # Create directories
    print("\n2. Creating directories...")
    create_directories()
    
    # Create HTML file
    print("\n3. Creating HTML file...")
    create_html_file()
    
    # Start the application
    print("\n4. Starting File Transfer System...")
    print("\nServer Information:")
    print("- Web Interface: http://localhost:5000")
    print("- TCP Receiver: localhost:9999")
    print("- Upload Directory: ./uploads")
    print("- Received Directory: ./received")
    
    print("\n" + "=" * 60)
    print("Starting server... (Press Ctrl+C to stop)")
    print("=" * 60)
    
    try:
        # Import and run the Flask app
        import app
        app.socketio.run(app.app, debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n\nShutting down File Transfer System...")
        print("Goodbye!")
    except Exception as e:
        print(f"\nError starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
