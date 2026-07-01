/**
 * Messages API — cross-device chat
 */
import api from './client'

export interface Message {
  id: number
  content: string
  sender: 'PC' | '手机'
  created_at: string
}

export async function fetchMessages(limit: number = 50): Promise<Message[]> {
  const { data } = await api.get('/messages', { params: { limit } })
  return data.messages
}

export async function postMessage(content: string, sender: string): Promise<Message> {
  const { data } = await api.post('/messages', { content, sender })
  return data
}

export async function deleteMessageApi(msgId: number): Promise<void> {
  await api.delete(`/messages/${msgId}`)
}

export async function clearMessagesApi(): Promise<number> {
  const { data } = await api.delete('/messages')
  return data.detail
}
