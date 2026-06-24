import { useState } from 'react'
import { Table, Button, Space, Popconfirm, Input, message, Typography, Empty } from 'antd'
import {
  FileOutlined,
  FolderOutlined,
  DownloadOutlined,
  DeleteOutlined,
  EditOutlined,
  MoreOutlined,
  FileImageOutlined,
  FilePdfOutlined,
  FileTextOutlined,
  FileZipOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { FileItem } from '../api/files'
import { downloadFileDirect, getDownloadToken, renameFile, deleteFile } from '../api/files'

const { Text } = Typography

interface FileTableProps {
  files: FileItem[]
  loading: boolean
  currentPath: string
  onRefresh: () => void
  onNavigate: (path: string) => void
}

function getFileIcon(item: FileItem) {
  if (item.is_dir) return <FolderOutlined className="folder-icon" />

  const ext = item.name.split('.').pop()?.toLowerCase()
  const iconMap: Record<string, React.ReactNode> = {
    jpg: <FileImageOutlined />, jpeg: <FileImageOutlined />, png: <FileImageOutlined />,
    gif: <FileImageOutlined />, svg: <FileImageOutlined />, webp: <FileImageOutlined />,
    bmp: <FileImageOutlined />,
    pdf: <FilePdfOutlined />,
    txt: <FileTextOutlined />, md: <FileTextOutlined />, log: <FileTextOutlined />,
    zip: <FileZipOutlined />, rar: <FileZipOutlined />, '7z': <FileZipOutlined />,
    tar: <FileZipOutlined />, gz: <FileZipOutlined />,
    mp4: <VideoCameraOutlined />, avi: <VideoCameraOutlined />, mkv: <VideoCameraOutlined />,
    mov: <VideoCameraOutlined />,
  }
  return iconMap[ext || ''] || <FileOutlined className="file-icon" />
}

export default function FileTable({ files, loading, currentPath, onRefresh, onNavigate }: FileTableProps) {
  const [renamingPath, setRenamingPath] = useState<string | null>(null)
  const [newName, setNewName] = useState('')

  const joinPath = (parent: string, name: string) => {
    if (parent === '/') return `/${name}`
    return `${parent}/${name}`
  }

  const handleDoubleClick = (item: FileItem) => {
    if (item.is_dir) {
      onNavigate(joinPath(currentPath, item.name))
    }
  }

  const handleDownload = async (item: FileItem) => {
    if (item.is_dir) return
    const filePath = joinPath(currentPath, item.name)
    try {
      const token = await getDownloadToken(filePath)
      downloadFileDirect(filePath, item.name, token)
    } catch {
      message.error('下载失败')
    }
  }

  const handleDelete = async (item: FileItem) => {
    try {
      await deleteFile(joinPath(currentPath, item.name))
      message.success(`已删除: ${item.name}`)
      onRefresh()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '删除失败')
    }
  }

  const handleRename = async (item: FileItem) => {
    if (!newName.trim() || newName === item.name) {
      setRenamingPath(null)
      return
    }
    try {
      await renameFile(joinPath(currentPath, item.name), newName.trim())
      message.success(`已重命名为: ${newName}`)
      setRenamingPath(null)
      onRefresh()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '重命名失败')
    }
  }

  const columns: ColumnsType<FileItem> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
      render: (name: string, record: FileItem) => {
        const fullPath = joinPath(currentPath, name)
        if (renamingPath === fullPath) {
          return (
            <Input
              size="small"
              autoFocus
              defaultValue={name}
              onChange={(e) => setNewName(e.target.value)}
              onPressEnter={() => handleRename(record)}
              onBlur={() => setRenamingPath(null)}
              style={{ maxWidth: 300 }}
            />
          )
        }
        return (
          <div
            className="file-name-cell"
            onDoubleClick={() => handleDoubleClick(record)}
          >
            {getFileIcon(record)}
            <a
              onClick={(e) => {
                if (record.is_dir) {
                  e.preventDefault()
                  handleDoubleClick(record)
                }
              }}
              style={{ color: record.is_dir ? '#1677ff' : 'inherit' }}
            >
              {name}
            </a>
          </div>
        )
      },
    },
    {
      title: '大小',
      dataIndex: 'size_display',
      key: 'size',
      width: 120,
      sorter: (a, b) => a.size - b.size,
      render: (size: string, record: FileItem) => (
        <Text type={record.is_dir ? 'secondary' : undefined}>
          {record.is_dir ? '-' : size}
        </Text>
      ),
    },
    {
      title: '修改时间',
      dataIndex: 'mtime_display',
      key: 'time',
      width: 180,
      sorter: (a, b) => a.mtime - b.mtime,
      responsive: ['md'],
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: FileItem) => {
        const fullPath = joinPath(currentPath, record.name)
        return (
          <Space onClick={(e) => e.stopPropagation()}>
            {!record.is_dir && (
              <Button
                type="text"
                size="small"
                icon={<DownloadOutlined />}
                onClick={() => handleDownload(record)}
              />
            )}
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => {
                setRenamingPath(fullPath)
                setNewName(record.name)
              }}
            />
            <Popconfirm
              title={record.is_dir ? '确定删除此文件夹及其所有内容？' : '确定删除此文件？'}
              onConfirm={() => handleDelete(record)}
              okText="删除"
              cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Button type="text" size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Space>
        )
      },
    },
  ]

  return (
    <Table
      columns={columns}
      dataSource={files}
      rowKey="name"
      loading={loading}
      pagination={false}
      size="middle"
      locale={{
        emptyText: (
          <Empty description="此目录为空" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ),
      }}
      onRow={(record) => ({
        onDoubleClick: () => handleDoubleClick(record),
        className: 'file-table-row',
      })}
    />
  )
}
