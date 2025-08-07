"use client"

import type React from "react"

import { useState, useRef, useCallback } from "react"
import { Upload, Play, Pause, X, Check, AlertCircle, FileText } from "lucide-react"

interface FileTransfer {
  id: string
  name: string
  size: number
  progress: number
  status: "pending" | "transferring" | "paused" | "completed" | "error"
  speed?: string
  timeRemaining?: string
}

interface LogEntry {
  id: string
  timestamp: string
  type: "info" | "success" | "error" | "warning"
  message: string
}

export default function FileTransferApp() {
  const [files, setFiles] = useState<FileTransfer[]>([])
  const [logs, setLogs] = useState<LogEntry[]>([
    {
      id: "1",
      timestamp: new Date().toLocaleTimeString(),
      type: "info",
      message: "File transfer system initialized",
    },
    {
      id: "2",
      timestamp: new Date().toLocaleTimeString(),
      type: "info",
      message: "Sender server: localhost:8001",
    },
    {
      id: "3",
      timestamp: new Date().toLocaleTimeString(),
      type: "info",
      message: "Receiver server: localhost:8002",
    },
  ])
  const [dragActive, setDragActive] = useState(false)
  const [notification, setNotification] = useState<{ type: "success" | "error" | "warning"; message: string } | null>(
    null,
  )
  const fileInputRef = useRef<HTMLInputElement>(null)
  const logEndRef = useRef<HTMLDivElement>(null)

  const addLog = useCallback((type: LogEntry["type"], message: string) => {
    const newLog: LogEntry = {
      id: Date.now().toString(),
      timestamp: new Date().toLocaleTimeString(),
      type,
      message,
    }
    setLogs((prev) => [...prev, newLog])
    setTimeout(() => {
      logEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }, 100)
  }, [])

  const showNotification = useCallback((type: "success" | "error" | "warning", message: string) => {
    setNotification({ type, message })
    setTimeout(() => setNotification(null), 5000)
  }, [])

  const validateFile = (file: File): string | null => {
    const maxSize = 100 * 1024 * 1024 // 100MB
    const allowedTypes = ["image/", "text/", "application/pdf", "application/zip"]

    if (file.size > maxSize) {
      return `File size exceeds 100MB limit (${(file.size / 1024 / 1024).toFixed(1)}MB)`
    }

    if (!allowedTypes.some((type) => file.type.startsWith(type))) {
      return `File type not supported: ${file.type}`
    }

    if (!/^[a-zA-Z0-9._-]+$/.test(file.name)) {
      return "File name contains invalid characters. Use only letters, numbers, dots, hyphens, and underscores."
    }

    return null
  }

  const handleFiles = useCallback(
    (fileList: FileList) => {
      const newFiles: FileTransfer[] = []
      const existingNames = files.map((f) => f.name)

      Array.from(fileList).forEach((file) => {
        const validation = validateFile(file)
        if (validation) {
          addLog("error", `${file.name}: ${validation}`)
          showNotification("error", validation)
          return
        }

        let fileName = file.name
        let counter = 1
        while (existingNames.includes(fileName) || newFiles.some((f) => f.name === fileName)) {
          const nameParts = file.name.split(".")
          const extension = nameParts.pop()
          const baseName = nameParts.join(".")
          fileName = `${baseName}_${counter}.${extension}`
          counter++
        }

        if (fileName !== file.name) {
          addLog("warning", `File renamed: ${file.name} → ${fileName}`)
          showNotification("warning", `File renamed to avoid duplicate: ${fileName}`)
        }

        const fileTransfer: FileTransfer = {
          id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
          name: fileName,
          size: file.size,
          progress: 0,
          status: "pending",
        }

        newFiles.push(fileTransfer)
        addLog("info", `File queued: ${fileName} (${(file.size / 1024 / 1024).toFixed(2)}MB)`)
      })

      setFiles((prev) => [...prev, ...newFiles])
    },
    [files, addLog, showNotification],
  )

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setDragActive(false)

      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files)
      }
    },
    [handleFiles],
  )

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFiles(e.target.files)
      }
    },
    [handleFiles],
  )

  const startTransfer = useCallback(
    (fileId: string) => {
      setFiles((prev) => prev.map((file) => (file.id === fileId ? { ...file, status: "transferring" as const } : file)))

      const file = files.find((f) => f.id === fileId)
      if (file) {
        addLog("info", `Starting transfer: ${file.name}`)

        // Simulate file transfer progress
        let progress = 0
        const interval = setInterval(() => {
          progress += Math.random() * 15
          if (progress >= 100) {
            progress = 100
            clearInterval(interval)
            setFiles((prev) =>
              prev.map((f) => (f.id === fileId ? { ...f, progress: 100, status: "completed" as const } : f)),
            )
            addLog("success", `Transfer completed: ${file.name}`)
            showNotification("success", `File transferred successfully: ${file.name}`)
          } else {
            setFiles((prev) =>
              prev.map((f) =>
                f.id === fileId
                  ? {
                      ...f,
                      progress,
                      speed: `${(Math.random() * 5 + 1).toFixed(1)} MB/s`,
                      timeRemaining: `${Math.ceil((100 - progress) / 10)}s`,
                    }
                  : f,
              ),
            )
          }
        }, 500)
      }
    },
    [files, addLog, showNotification],
  )

  const pauseTransfer = useCallback(
    (fileId: string) => {
      setFiles((prev) => prev.map((file) => (file.id === fileId ? { ...file, status: "paused" as const } : file)))
      const file = files.find((f) => f.id === fileId)
      if (file) {
        addLog("warning", `Transfer paused: ${file.name}`)
      }
    },
    [files, addLog],
  )

  const removeFile = useCallback(
    (fileId: string) => {
      const file = files.find((f) => f.id === fileId)
      setFiles((prev) => prev.filter((f) => f.id !== fileId))
      if (file) {
        addLog("info", `File removed: ${file.name}`)
      }
    },
    [files, addLog],
  )

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes"
    const k = 1024
    const sizes = ["Bytes", "KB", "MB", "GB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
  }

  const getStatusColor = (status: FileTransfer["status"]) => {
    switch (status) {
      case "pending":
        return "text-gray-500"
      case "transferring":
        return "text-blue-500"
      case "paused":
        return "text-yellow-500"
      case "completed":
        return "text-green-500"
      case "error":
        return "text-red-500"
      default:
        return "text-gray-500"
    }
  }

  const getLogColor = (type: LogEntry["type"]) => {
    switch (type) {
      case "info":
        return "text-gray-300"
      case "success":
        return "text-green-400"
      case "error":
        return "text-red-400"
      case "warning":
        return "text-yellow-400"
      default:
        return "text-gray-300"
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">File Transfer System</h1>
          <p className="text-gray-600">TCP Socket-based file transfer between localhost servers</p>
        </div>

        {/* Notification */}
        {notification && (
          <div
            className={`mb-6 p-4 rounded-lg border-l-4 ${
              notification.type === "success"
                ? "bg-green-50 border-green-400 text-green-700"
                : notification.type === "error"
                  ? "bg-red-50 border-red-400 text-red-700"
                  : "bg-yellow-50 border-yellow-400 text-yellow-700"
            }`}
          >
            <div className="flex items-center">
              {notification.type === "success" && <Check className="w-5 h-5 mr-2" />}
              {notification.type === "error" && <AlertCircle className="w-5 h-5 mr-2" />}
              {notification.type === "warning" && <AlertCircle className="w-5 h-5 mr-2" />}
              {notification.message}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* File Upload Area */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Upload Files</h2>

              <div
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  dragActive ? "border-blue-400 bg-blue-50" : "border-gray-300 hover:border-gray-400"
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-lg font-medium text-gray-700 mb-2">Drop files here or click to browse</p>
                <p className="text-sm text-gray-500 mb-4">
                  Supports images, documents, PDFs, and ZIP files up to 100MB
                </p>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
                >
                  Choose Files
                </button>
                <input ref={fileInputRef} type="file" multiple onChange={handleFileInput} className="hidden" />
              </div>
            </div>

            {/* File List and Progress */}
            {files.length > 0 && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">File Transfers</h2>

                <div className="space-y-4">
                  {files.map((file) => (
                    <div key={file.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-3">
                          <FileText className="w-5 h-5 text-gray-400" />
                          <div>
                            <p className="font-medium text-gray-900">{file.name}</p>
                            <p className="text-sm text-gray-500">{formatFileSize(file.size)}</p>
                          </div>
                        </div>

                        <div className="flex items-center space-x-2">
                          <span className={`text-sm font-medium capitalize ${getStatusColor(file.status)}`}>
                            {file.status}
                          </span>

                          {file.status === "pending" && (
                            <button
                              onClick={() => startTransfer(file.id)}
                              className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                              title="Start Transfer"
                            >
                              <Play className="w-4 h-4" />
                            </button>
                          )}

                          {file.status === "transferring" && (
                            <button
                              onClick={() => pauseTransfer(file.id)}
                              className="p-2 text-yellow-600 hover:bg-yellow-50 rounded-lg transition-colors"
                              title="Pause Transfer"
                            >
                              <Pause className="w-4 h-4" />
                            </button>
                          )}

                          {file.status === "paused" && (
                            <button
                              onClick={() => startTransfer(file.id)}
                              className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                              title="Resume Transfer"
                            >
                              <Play className="w-4 h-4" />
                            </button>
                          )}

                          <button
                            onClick={() => removeFile(file.id)}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            title="Remove File"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="mb-2">
                        <div className="flex justify-between text-sm text-gray-600 mb-1">
                          <span>{file.progress.toFixed(1)}%</span>
                          {file.speed && file.timeRemaining && (
                            <span>
                              {file.speed} • {file.timeRemaining} remaining
                            </span>
                          )}
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full transition-all duration-300 ${
                              file.status === "completed"
                                ? "bg-green-500"
                                : file.status === "error"
                                  ? "bg-red-500"
                                  : file.status === "paused"
                                    ? "bg-yellow-500"
                                    : "bg-blue-500"
                            }`}
                            style={{ width: `${file.progress}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* CLI Log Area */}
          <div className="lg:col-span-1">
            <div className="bg-gray-900 rounded-xl shadow-sm border border-gray-700 p-6 h-96 lg:h-[600px]">
              <div className="flex items-center space-x-2 mb-4">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span className="text-gray-400 text-sm ml-2">Transfer Log</span>
              </div>

              <div className="h-full overflow-y-auto font-mono text-sm">
                {logs.map((log) => (
                  <div key={log.id} className="mb-1">
                    <span className="text-gray-500">[{log.timestamp}]</span>
                    <span className={`ml-2 ${getLogColor(log.type)}`}>{log.message}</span>
                  </div>
                ))}
                <div ref={logEndRef} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
