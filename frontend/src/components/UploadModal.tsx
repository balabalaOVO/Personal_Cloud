import { useState, useRef } from 'react'
import { Modal, Button, Progress, Typography, Tag, message } from 'antd'
import {
  UploadOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  InboxOutlined,
} from '@ant-design/icons'
import { uploadFile } from '../api/files'
import { computeSHA256, formatSize, formatSpeed } from '../utils/hash'

const { Text } = Typography

interface UploadModalProps {
  open: boolean
  currentPath: string
  onClose: () => void
  onSuccess: () => void
}

interface UploadTask {
  id: string
  file: File
  progress: number
  speed: number
  status: 'pending' | 'uploading' | 'done' | 'error'
  sha256?: string
  sha256Match?: boolean
  error?: string
}

export default function UploadModal({ open, currentPath, onClose, onSuccess }: UploadModalProps) {
  const [tasks, setTasks] = useState<UploadTask[]>([])
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const addFiles = (files: FileList) => {
    const newTasks: UploadTask[] = []
    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      // Don't compute SHA-256 here — it reads the entire file into memory
      // and blocks the UI for large files. We'll compute it during upload
      // only for reasonably-sized files.
      newTasks.push({
        id: `${Date.now()}-${i}`,
        file,
        progress: 0,
        speed: 0,
        status: 'pending',
        sha256: '',  // computed on-demand during upload
      })
    }
    setTasks((prev) => [...prev, ...newTasks])
  }

  const startUpload = async () => {
    setUploading(true)
    const pending = tasks.filter((t) => t.status === 'pending')

    for (const task of pending) {
      setTasks((prev) =>
        prev.map((t) => (t.id === task.id ? { ...t, status: 'uploading' as const } : t))
      )

      // Compute SHA-256 just-in-time, only for files under 500MB
      // (larger files skip frontend hash to avoid memory issues;
      //  backend still verifies integrity)
      let sha256 = ''
      const MAX_HASH_SIZE = 500 * 1024 * 1024  // 500 MB
      if (task.file.size <= MAX_HASH_SIZE) {
        try {
          sha256 = await computeSHA256(task.file)
          setTasks((prev) =>
            prev.map((t) =>
              t.id === task.id ? { ...t, sha256 } : t
            )
          )
        } catch {
          // Hash computation failed (e.g. out of memory) — skip it
        }
      }

      try {
        const result = await uploadFile(
          task.file,
          currentPath,
          sha256,
          (percent, speed) => {
            setTasks((prev) =>
              prev.map((t) =>
                t.id === task.id ? { ...t, progress: percent, speed } : t
              )
            )
          }
        )

        setTasks((prev) =>
          prev.map((t) =>
            t.id === task.id
              ? {
                  ...t,
                  status: 'done' as const,
                  progress: 100,
                  sha256Match: result.sha256_match,
                }
              : t
          )
        )
      } catch (err: any) {
        setTasks((prev) =>
          prev.map((t) =>
            t.id === task.id
              ? {
                  ...t,
                  status: 'error' as const,
                  error: err.response?.data?.detail || 'Upload failed',
                }
              : t
          )
        )
      }
    }

    setUploading(false)
    const anySuccess = tasks.some((t) => t.status === 'done')
    if (anySuccess) {
      message.success('上传完成')
      onSuccess()
    }
  }

  const handleClose = () => {
    if (!uploading) {
      setTasks([])
      onClose()
    }
  }

  const allDone = tasks.length > 0 && tasks.every((t) => t.status === 'done' || t.status === 'error')

  return (
    <Modal
      title="上传文件"
      open={open}
      onCancel={handleClose}
      footer={null}
      width={560}
      className="upload-progress-modal"
      maskClosable={!uploading}
    >
      {tasks.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <InboxOutlined style={{ fontSize: 56, color: '#d9d9d9' }} />
          <div style={{ marginTop: 16, marginBottom: 24 }}>
            <Text type="secondary">点击或拖拽文件到此处上传</Text>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files) addFiles(e.target.files)
              e.target.value = ''
            }}
          />
          <Button type="primary" icon={<UploadOutlined />} onClick={() => fileInputRef.current?.click()}>
            选择文件
          </Button>
          <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
            禁止上传 .exe .sh .bat 等可执行文件
          </Text>
        </div>
      ) : (
        <div>
          {tasks.map((task) => (
            <div key={task.id} className="upload-progress-item" style={{ marginBottom: 12 }}>
              <div className="file-info" style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Text strong style={{ fontSize: 14 }} ellipsis={{ tooltip: task.file.name }}>
                    {task.file.name}
                  </Text>
                  <span style={{ marginLeft: 8, flexShrink: 0 }}>
                    {task.status === 'uploading' && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {task.progress}%
                      </Text>
                    )}
                    {task.status === 'done' && (
                      task.sha256Match !== false
                        ? <Tag color="success" icon={<CheckCircleFilled />}>校验通过</Tag>
                        : <Tag color="error" icon={<CloseCircleFilled />}>校验失败</Tag>
                    )}
                    {task.status === 'error' && (
                      <Tag color="error">失败</Tag>
                    )}
                    {task.status === 'pending' && (
                      <Text type="secondary" style={{ fontSize: 12 }}>等待上传</Text>
                    )}
                  </span>
                </div>
                {(task.status === 'uploading' || task.status === 'done') && (
                  <Progress
                    percent={task.progress}
                    size="small"
                    status={task.status === 'done' ? 'success' : 'active'}
                    style={{ marginTop: 4, marginBottom: 0 }}
                  />
                )}
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {formatSize(task.file.size)}
                  {task.speed > 0 && task.status === 'uploading' && ` · ${formatSpeed(task.speed)}`}
                </Text>
                {task.error && (
                  <Text type="danger" style={{ fontSize: 12 }}>{task.error}</Text>
                )}
              </div>
            </div>
          ))}

          <div style={{ marginTop: 16, display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            {!uploading && !allDone && (
              <Button onClick={() => fileInputRef.current?.click()}>
                添加更多文件
              </Button>
            )}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              style={{ display: 'none' }}
              onChange={(e) => {
                if (e.target.files) addFiles(e.target.files)
                e.target.value = ''
              }}
            />
            {!uploading && !allDone && (
              <Button type="primary" onClick={startUpload} disabled={tasks.length === 0}>
                开始上传
              </Button>
            )}
            {allDone && (
              <Button type="primary" onClick={handleClose}>
                完成
              </Button>
            )}
          </div>
        </div>
      )}
    </Modal>
  )
}
