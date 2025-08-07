# 🚀 File Transfer System - TCP Socket Implementation

A modern, web-based file transfer application built with Python Flask and TCP sockets. Features real-time progress tracking, drag-and-drop uploads, and a beautiful user interface.

## ✨ Features

- **Real TCP Socket Transfer**: Actual networking implementation using Python sockets
- **Drag & Drop Interface**: Modern web UI with drag-and-drop file uploads
- **Real-time Progress**: Live progress bars with transfer speed and ETA
- **Pause/Resume**: Control file transfers with pause and resume functionality
- **CLI-style Logging**: Terminal-like log output for transfer history
- **File Validation**: Size limits, type checking, and filename validation
- **Duplicate Handling**: Automatic file renaming for duplicates
- **Success Notifications**: Toast notifications for transfer completion
- **Responsive Design**: Professional, minimalistic interface

## 🏃‍♂️ Quick Start

### Option 1: One-Command Start (Recommended)
\`\`\`bash
python run.py
\`\`\`

### Option 2: Manual Start
\`\`\`bash
# Install requirements
pip install Flask==2.3.3 Flask-SocketIO==5.3.6

# Run the application
python app.py
\`\`\`

## 📁 Project Structure

\`\`\`
file-transfer-system/
├── app.py              # Main Flask application with TCP sockets
├── index.html          # Frontend user interface
├── requirements.txt    # Python dependencies
├── run.py             # Quick start script
├── README.md          # This file
├── uploads/           # Temporary upload storage (auto-created)
└── received/          # Final file destination (auto-created)
\`\`\`

## 🌐 Usage

1. **Start the system**: Run `python run.py`
2. **Open browser**: Navigate to `http://localhost:5000`
3. **Upload files**: Drag files to the upload area or click to browse
4. **Start transfer**: Click the play button to begin TCP transfer
5. **Monitor progress**: Watch real-time progress and logs
6. **Check results**: Files appear in the `received/` folder

## 🔧 Technical Details

- **Backend**: Python Flask with SocketIO for real-time updates
- **TCP Server**: Custom socket server on localhost:9999
- **Frontend**: Vanilla HTML/CSS/JavaScript with modern design
- **File Transfer**: Chunked transfer with progress tracking
- **Validation**: File size (100MB max), filename, and type checking
- **Error Handling**: Comprehensive error handling and user feedback

## 📋 Requirements

- Python 3.7+
- Flask 2.3.3
- Flask-SocketIO 5.3.6
- Modern web browser

## 🚀 System Architecture

\`\`\`
Web Browser (Frontend)
    ↕ HTTP/WebSocket
Flask Web Server
    ↕ TCP Socket
TCP Receiver Server
    ↓ File I/O
Local File System
\`\`\`

## 🛠️ Configuration

The system uses these default settings:
- Web server: `localhost:5000`
- TCP receiver: `localhost:9999`
- Max file size: `100MB`
- Chunk size: `4KB`

## 📝 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

---

**Made with ❤️ using Python, Flask, and TCP Sockets**
