#!/usr/bin/env python3
"""
File Transfer System - Quick Start Script
This script automatically sets up and runs the complete file transfer system.
"""

import subprocess
import sys
import os
import time

def print_banner():
    """Print welcome banner"""
    print("\n" + "="*70)
    print("🚀 FILE TRANSFER SYSTEM - TCP SOCKET IMPLEMENTATION")
    print("="*70)
    print("📋 Features:")
    print("   • Real TCP socket file transfer")
    print("   • Drag & drop file upload")
    print("   • Real-time progress tracking")
    print("   • Pause/resume transfers")
    print("   • CLI-style logging")
    print("   • File validation & duplicate handling")
    print("="*70)

def install_requirements():
    """Install required Python packages"""
    print("\n📦 Installing required packages...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "Flask==2.3.3", 
            "Flask-SocketIO==5.3.6",
            "python-socketio==5.8.0",
            "python-engineio==4.7.1"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ All packages installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install packages: {e}")
        print("💡 Try running: pip install -r requirements.txt")
        return False

def check_files():
    """Check if required files exist"""
    required_files = ['app.py', 'index.html']
    missing_files = []
    
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    print("✅ All required files found!")
    return True

def main():
    """Main function to set up and run the system"""
    print_banner()
    
    # Check if required files exist
    if not check_files():
        print("\n❌ Setup failed - missing required files")
        sys.exit(1)
    
    # Install requirements
    if not install_requirements():
        print("\n❌ Setup failed - could not install requirements")
        sys.exit(1)
    
    print("\n🔧 Starting File Transfer System...")
    print("\n" + "="*70)
    print("🌐 Server will start on: http://localhost:5000")
    print("🔌 TCP receiver will run on: localhost:9999")
    print("📁 Upload folder: ./uploads")
    print("📥 Received folder: ./received")
    print("="*70)
    print("\n💡 Open http://localhost:5000 in your browser")
    print("⏹️  Press Ctrl+C to stop the server")
    print("\n🚀 Starting in 3 seconds...")
    
    time.sleep(3)
    
    try:
        # Import and run the main application
        import app
        print("\n✅ System started successfully!")
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        print("👋 Goodbye!")
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("💡 Make sure all files are in the same directory")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
