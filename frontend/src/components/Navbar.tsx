import { useState, useEffect } from 'react'
import { Button, Dropdown, Avatar, Space, Typography, Popover } from 'antd'
import {
  CloudOutlined,
  LogoutOutlined,
  UserOutlined,
  FolderOutlined,
  MessageOutlined,
  QrcodeOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import axios from 'axios'
import QRCode from 'qrcode'
import { clearAuth } from '../api/client'

const { Text } = Typography

export default function Navbar() {
  const navigate = useNavigate()
  const location = useLocation()
  const [lanUrl, setLanUrl] = useState<string>('')
  const [qrDataUrl, setQrDataUrl] = useState<string>('')

  const isMessages = location.pathname.startsWith('/messages')

  useEffect(() => {
    axios.get('/api/public-status').then((res) => {
      const { mdns, bind_port, protocol } = res.data
      if (mdns?.lan_ip) {
        const url = `http://${mdns.lan_ip}:${bind_port}`
        setLanUrl(url)
        QRCode.toDataURL(url, { width: 160, margin: 1 }).then(setQrDataUrl).catch(() => {})
      }
    }).catch(() => {})
  }, [])

  const handleLogout = () => {
    clearAuth()
    navigate('/login', { replace: true })
  }

  const userMenu = {
    items: [
      {
        key: 'logout',
        icon: <LogoutOutlined />,
        label: '退出登录',
        onClick: handleLogout,
      },
    ],
  }

  const qrPopover = (
    <div style={{ textAlign: 'center' }}>
      {qrDataUrl ? (
        <img src={qrDataUrl} alt="QR" style={{ display: 'block', margin: '0 auto' }} />
      ) : (
        <Text type="secondary">加载中...</Text>
      )}
      {lanUrl && (
        <Text copyable style={{ fontSize: 12, display: 'block', marginTop: 8 }}>
          {lanUrl}
        </Text>
      )}
      <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 4 }}>
        手机扫码即可访问
      </Text>
    </div>
  )

  return (
    <div className="file-navbar">
      <div className="navbar-left">
        <div className="brand">
          <CloudOutlined style={{ fontSize: 24, color: '#1677ff' }} />
          <Text strong style={{ fontSize: 18, color: '#1677ff' }}>
            AI 个人云盘
          </Text>
        </div>

        <div className="navbar-tabs">
          <Button
            type={isMessages ? 'text' : 'primary'}
            ghost={!isMessages}
            icon={<FolderOutlined />}
            onClick={() => navigate('/')}
          >
            文件
          </Button>
          <Button
            type={isMessages ? 'primary' : 'text'}
            ghost={!isMessages}
            icon={<MessageOutlined />}
            onClick={() => navigate('/messages')}
          >
            消息
          </Button>
        </div>
      </div>

      <Space>
        {lanUrl && (
          <Popover content={qrPopover} trigger="click" placement="bottomRight">
            <Button type="text" icon={<QrcodeOutlined />} title="手机扫码访问" />
          </Popover>
        )}
        <Dropdown menu={userMenu} placement="bottomRight">
          <Button type="text" icon={<Avatar size="small" icon={<UserOutlined />} />}>
            admin
          </Button>
        </Dropdown>
      </Space>
    </div>
  )
}
