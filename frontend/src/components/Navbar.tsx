import { Button, Dropdown, Avatar, Space, Typography } from 'antd'
import {
  CloudOutlined,
  LogoutOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { clearAuth } from '../api/client'

const { Text } = Typography

export default function Navbar() {
  const navigate = useNavigate()

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

  return (
    <div className="file-navbar">
      <div className="brand">
        <CloudOutlined style={{ fontSize: 24, color: '#1677ff' }} />
        <Text strong style={{ fontSize: 18, color: '#1677ff' }}>
          AI 个人云盘
        </Text>
      </div>

      <Space>
        <Dropdown menu={userMenu} placement="bottomRight">
          <Button type="text" icon={<Avatar size="small" icon={<UserOutlined />} />}>
            admin
          </Button>
        </Dropdown>
      </Space>
    </div>
  )
}
