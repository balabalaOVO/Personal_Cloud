import { useEffect, useRef } from 'react'
import { Typography, Empty } from 'antd'
import { MessageOutlined } from '@ant-design/icons'
import type { Message } from '../api/messages'

const { Text } = Typography

interface ChatBoxProps {
  messages: Message[]
  currentSender: string
}

function formatTime(iso: string) {
  const d = new Date(iso + 'Z')
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

export default function ChatBox({ messages, currentSender }: ChatBoxProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="chat-empty">
        <Empty
          image={<MessageOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
          description="暂无消息，发送第一条吧"
        />
      </div>
    )
  }

  return (
    <div className="chat-list">
      {messages.map((msg) => {
        const isMine = msg.sender === currentSender
        return (
          <div
            key={msg.id}
            className={`chat-bubble ${isMine ? 'chat-bubble-mine' : 'chat-bubble-other'}`}
          >
            <div className="chat-bubble-sender">
              <Text type="secondary" style={{ fontSize: 12 }}>
                {msg.sender === 'PC' ? '💻 PC' : '📱 手机'}
              </Text>
            </div>
            <div className="chat-bubble-content">{msg.content}</div>
            <div className="chat-bubble-time">
              <Text type="secondary" style={{ fontSize: 11 }}>
                {formatTime(msg.created_at)}
              </Text>
            </div>
          </div>
        )
      })}
      <div ref={bottomRef} />
    </div>
  )
}
