import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Breadcrumb, Button, Input, Space, message, Typography, Spin } from 'antd'
import {
  UploadOutlined,
  FolderAddOutlined,
  ReloadOutlined,
  HomeOutlined,
  ArrowUpOutlined,
} from '@ant-design/icons'
import Navbar from '../components/Navbar'
import FileTable from '../components/FileTable'
import UploadModal from '../components/UploadModal'
import { fetchFiles, mkdir, type FileItem } from '../api/files'

const { Text } = Typography

export default function FilePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const currentPath = searchParams.get('path') || '/'

  const [files, setFiles] = useState<FileItem[]>([])
  const [loading, setLoading] = useState(true)
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [creatingFolder, setCreatingFolder] = useState(false)

  const loadFiles = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchFiles(currentPath)
      setFiles(data.items)
    } catch (err: any) {
      message.error(err.response?.data?.detail || '加载文件列表失败')
    } finally {
      setLoading(false)
    }
  }, [currentPath])

  useEffect(() => {
    loadFiles()
  }, [loadFiles])

  const navigateTo = (path: string) => {
    setSearchParams({ path })
  }

  const goUp = () => {
    if (currentPath === '/') return
    const parts = currentPath.replace(/\/$/, '').split('/')
    parts.pop()
    navigateTo(parts.join('/') || '/')
  }

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return
    setCreatingFolder(true)
    try {
      await mkdir(currentPath, newFolderName.trim())
      message.success(`文件夹已创建: ${newFolderName}`)
      setNewFolderName('')
      loadFiles()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '创建文件夹失败')
    } finally {
      setCreatingFolder(false)
    }
  }

  // Build breadcrumb items
  const pathParts = currentPath.split('/').filter(Boolean)
  const breadcrumbItems = [
    {
      title: (
        <a onClick={() => navigateTo('/')}>
          <HomeOutlined /> 根目录
        </a>
      ),
    },
    ...pathParts.map((part, i) => {
      const fullPath = '/' + pathParts.slice(0, i + 1).join('/')
      const isLast = i === pathParts.length - 1
      return {
        title: isLast ? (
          <Text strong>{decodeURIComponent(part)}</Text>
        ) : (
          <a onClick={() => navigateTo(fullPath)}>{decodeURIComponent(part)}</a>
        ),
      }
    }),
  ]

  return (
    <div className="file-page">
      <Navbar />

      {/* Breadcrumb + toolbar */}
      <div className="breadcrumb-bar">
        <Space>
          {currentPath !== '/' && (
            <Button
              type="text"
              icon={<ArrowUpOutlined />}
              onClick={goUp}
              title="返回上级"
            />
          )}
          <Breadcrumb items={breadcrumbItems} />
        </Space>
        <Button
          type="text"
          icon={<ReloadOutlined />}
          onClick={loadFiles}
        />
      </div>

      {/* Toolbar */}
      <div className="file-toolbar">
        <Button type="primary" icon={<UploadOutlined />} onClick={() => setUploadModalOpen(true)}>
          上传文件
        </Button>

        <Space.Compact>
          <Input
            placeholder="新建文件夹名称"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            onPressEnter={handleCreateFolder}
            style={{ width: 180 }}
          />
          <Button
            icon={<FolderAddOutlined />}
            loading={creatingFolder}
            onClick={handleCreateFolder}
          >
            新建
          </Button>
        </Space.Compact>

        <Text type="secondary" style={{ marginLeft: 'auto' }}>
          共 {files.length} 项
        </Text>
      </div>

      {/* File table */}
      <div className="file-content">
        <FileTable
          files={files}
          loading={loading}
          currentPath={currentPath}
          onRefresh={loadFiles}
          onNavigate={navigateTo}
        />
      </div>

      {/* Upload modal */}
      <UploadModal
        open={uploadModalOpen}
        currentPath={currentPath}
        onClose={() => setUploadModalOpen(false)}
        onSuccess={loadFiles}
      />
    </div>
  )
}
