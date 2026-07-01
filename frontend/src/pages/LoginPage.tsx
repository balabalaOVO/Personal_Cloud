import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Form, Input, Button, message, Typography, Space, Tag } from 'antd'
import { CloudOutlined, UserOutlined, LockOutlined, WifiOutlined, GlobalOutlined } from '@ant-design/icons'
import axios from 'axios'
import QRCode from 'qrcode'
import { login } from '../api/auth'

const { Title, Text } = Typography

export default function LoginPage() {
  const [loading, setLoading] = useState(false)
  const [lanUrl, setLanUrl] = useState<string>('')
  const [domainUrl, setDomainUrl] = useState<string>('')
  const [qrDataUrl, setQrDataUrl] = useState<string>('')
  const navigate = useNavigate()

  useEffect(() => {
    axios.get('/api/public-status').then((res) => {
      const { mdns, bind_port, protocol, domain } = res.data
      if (mdns?.lan_ip) {
        const url = `http://${mdns.lan_ip}:${bind_port}`
        setLanUrl(url)
        // Generate QR code as base64 image
        QRCode.toDataURL(url, { width: 200, margin: 1 }).then(setQrDataUrl).catch(() => {})
      }
      if (domain) {
        setDomainUrl(`https://${domain}`)
      }
    }).catch(() => {})
  }, [])

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      await login(values.username, values.password)
      message.success('登录成功')
      navigate('/', { replace: true })
    } catch (err: any) {
      const detail = err.response?.data?.detail || '登录失败，请检查用户名和密码'
      message.error(detail)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <Card className="login-card" bordered={false}>
        <div className="login-header">
          <div className="logo-icon">
            <CloudOutlined style={{ fontSize: 48, color: '#1677ff' }} />
          </div>
          <Title level={3} style={{ marginBottom: 4 }}>AI 个人云盘</Title>
          <Text type="secondary">安全、高速的私有云存储</Text>
        </div>

        <Form
          name="login"
          onFinish={onFinish}
          size="large"
          autoComplete="off"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="用户名"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密码"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{ height: 44 }}
            >
              登录
            </Button>
          </Form.Item>
        </Form>

        {/* Network access info */}
        {(lanUrl || domainUrl) && (
          <div className="login-network-info">
            {lanUrl && (
              <div className="login-network-item">
                <div className="login-lan-row">
                  <div className="login-lan-info">
                    <Space>
                      <WifiOutlined style={{ color: '#52c41a' }} />
                      <Tag color="green">高速</Tag>
                    </Space>
                    <Text copyable style={{ fontSize: 13 }}>
                      {lanUrl}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      手机扫码或输入此地址，极速传输
                    </Text>
                  </div>
                  {qrDataUrl && (
                    <div className="login-qrcode">
                      <img src={qrDataUrl} alt="手机扫码访问" width={100} height={100} />
                    </div>
                  )}
                </div>
              </div>
            )}
            {domainUrl && (
              <div className="login-network-item" style={{ marginTop: lanUrl ? 12 : 0 }}>
                <Space>
                  <GlobalOutlined style={{ color: '#1677ff' }} />
                  <Tag color="blue">远程</Tag>
                </Space>
                <Text copyable style={{ fontSize: 13 }}>
                  {domainUrl}
                </Text>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  任何网络都能访问，速度受限于 Cloudflare
                </Text>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
