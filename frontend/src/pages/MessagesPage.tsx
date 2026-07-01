import { useState, useEffect, useCallback, useRef } from 'react'
import { Button, Input, Segmented, Space, Typography, message, Popconfirm } from 'antd'
import {
  SendOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import Navbar from '../components/Navbar'
import ChatBox from '../components/ChatBox'
import { fetchMessages, postMessage, clearMessagesApi } from '../api/messages'
import type { Message } from '../api/messages'

const { Text } = Typography

function detectDevice(): string {
  const ua = navigator.userAgent
  if (/Android|iPhone|iPad|iPod|webOS/i.test(ua)) {
    return '手机'
  }
  return 'PC'
}

export default function MessagesPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [inputValue, setInputValue] = useState('')
  const [sender, setSender] = useState<string>(detectDevice)
  const [sending, setSending] = useState(false)
  const pollingRef = useRef<ReturnType<typeof setInterval>>()

  const loadMessages = useCallback(async () => {
    try {
      const data = await fetchMessages(50)
      setMessages(data)
    } catch (err: any) {
      // silent fail on poll — avoid spam on every interval
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial load
  useEffect(() => {
    loadMessages()
  }, [loadMessages])

  // Poll every 3 seconds
  useEffect(() => {
    pollingRef.current = setInterval(loadMessages, 3000)
    return () => clearInterval(pollingRef.current)
  }, [loadMessages])

  const handleSend = async () => {
    if (!inputValue.trim()) return
    setSending(true)
    try {
      await postMessage(inputValue.trim(), sender)
      setInputValue('')
      await loadMessages()
    } catch (err: any) {
      message.error(err.response?.data?.detail || '发送失败')
    } finally {
      setSending(false)
    }
  }

  const handleClear = async () => {
    try {
      await clearMessagesApi()
      setMessages([])
      message.success('已清空全部消息')
    } catch (err: any) {
      message.error('清空失败')
    }
  }

  const senderOptions = [
    { label: '💻 PC', value: 'PC' },
    { label: '📱 手机', value: '手机' },
  ]

  return (
    <div className="messages-page">
      <Navbar />

      <div className="messages-header">
        <Text strong style={{ fontSize: 16 }}>💬 消息</Text>
        <Popconfirm
          title="确定清空全部消息？"
          onConfirm={handleClear}
          okText="确定"
          cancelText="取消"
        >
          <Button type="text" danger icon={<DeleteOutlined />} size="small">
            清空
          </Button>
        </Popconfirm>
      </div>

      <div className="messages-body">
        {loading ? null : (
          <ChatBox messages={messages} currentSender={sender} />
        )}
      </div>

      <div className="messages-footer">
        <Space.Compact style={{ width: '100%' }}>
          <Segmented
            options={senderOptions}
            value={sender}
            onChange={(val) => setSender(val as string)}
          />
          <Input
            placeholder="输入消息..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onPressEnter={handleSend}
            style={{ flex: 1 }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            loading={sending}
            onClick={handleSend}
          >
            发送
          </Button>
        </Space.Compact>
      </div>
    </div>
  )
}
