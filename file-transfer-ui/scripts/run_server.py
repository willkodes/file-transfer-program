#!/usr/bin/env python3
"""
File Transfer System - TCP Socket Implementation
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
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Requirements installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install requirements: {e}")
        sys.exit(1)

def create_directories():
    """Create necessary directories"""
    directories = ['uploads', 'received', 'templates']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Directory created: {directory}")

def main():
    print("=" * 60)
    print("FILE TRANSFER SYSTEM - TCP SOCKET IMPLEMENTATION")
    print("=" * 60)
    
    # Install requirements
    print("\n1. Installing requirements...")
    install_requirements()
    
    # Create directories
    print("\n2. Creating directories...")
    create_directories()
    
    # Start the application
    print("\n3. Starting File Transfer System...")
    print("\nServer Information:")
    print("- Web Interface: http://localhost:5000")
    print("- TCP Receiver: localhost:9999")
    print("- Upload Directory: ./uploads")
    print("- Received Directory: ./received")
    
    print("\nFeatures:")
    print("- Real TCP socket file transfer")
    print("- Drag & drop file upload")
    print("- Real-time progress tracking")
    print("- Pause/resume transfers")
    print("- CLI-style logging")
    print("- File validation")
    print("- Duplicate file handling")
    
    print("\n" + "=" * 60)
    print("Starting server... (Press Ctrl+C to stop)")
    print("=" * 60)
    
    try:
        # Import and run the Flask app
        from app import app, socketio
        socketio.run(app, debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n\nShutting down File Transfer System...")
        print("Goodbye!")
    except Exception as e:
        print(f"\nError starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
