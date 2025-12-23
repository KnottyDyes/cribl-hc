import { useEffect, useRef, useState, useCallback } from 'react'

export interface WebSocketMessage {
  type: string
  [key: string]: any
}

interface UseWebSocketOptions {
  url: string
  onMessage?: (message: WebSocketMessage) => void
  onOpen?: () => void
  onClose?: () => void
  onError?: (error: Event) => void
  reconnectInterval?: number
  maxReconnectAttempts?: number
  enabled?: boolean
}

interface UseWebSocketReturn {
  isConnected: boolean
  isReconnecting: boolean
  reconnectAttempts: number
  sendMessage: (message: WebSocketMessage) => void
  disconnect: () => void
  connect: () => void
}

/**
 * Custom hook for managing WebSocket connections with automatic reconnection
 *
 * Features:
 * - Automatic reconnection with exponential backoff
 * - Connection state management
 * - Message sending with connection checks
 * - Manual connect/disconnect control
 * - Cleanup on unmount
 *
 * @example
 * ```tsx
 * const { isConnected, sendMessage } = useWebSocket({
 *   url: 'ws://localhost:8080/api/v1/analysis/ws/abc123',
 *   onMessage: (msg) => console.log('Received:', msg),
 *   maxReconnectAttempts: 5,
 * })
 * ```
 */
export function useWebSocket({
  url,
  onMessage,
  onOpen,
  onClose,
  onError,
  reconnectInterval = 3000,
  maxReconnectAttempts = 5,
  enabled = true,
}: UseWebSocketOptions): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isReconnecting, setIsReconnecting] = useState(false)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  const shouldReconnectRef = useRef(true)

  const connect = useCallback(() => {
    if (!enabled || wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected:', url)
        setIsConnected(true)
        setIsReconnecting(false)
        setReconnectAttempts(0)
        shouldReconnectRef.current = true
        onOpen?.()
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage
          onMessage?.(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        onError?.(error)
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected:', url)
        setIsConnected(false)
        onClose?.()

        // Attempt reconnection if not manually disconnected
        if (shouldReconnectRef.current && reconnectAttempts < maxReconnectAttempts) {
          setIsReconnecting(true)
          const nextAttempt = reconnectAttempts + 1
          setReconnectAttempts(nextAttempt)

          // Exponential backoff: 3s, 6s, 12s, 24s, 48s
          const backoffDelay = Math.min(
            reconnectInterval * Math.pow(2, reconnectAttempts),
            30000 // Max 30 seconds
          )

          console.log(
            `WebSocket reconnecting in ${backoffDelay}ms (attempt ${nextAttempt}/${maxReconnectAttempts})`
          )

          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, backoffDelay)
        } else if (reconnectAttempts >= maxReconnectAttempts) {
          console.error('WebSocket max reconnect attempts reached')
          setIsReconnecting(false)
        }
      }
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      setIsConnected(false)
    }
  }, [
    url,
    enabled,
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnectInterval,
    maxReconnectAttempts,
    reconnectAttempts,
  ])

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false
    setIsReconnecting(false)

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  const sendMessage = useCallback(
    (message: WebSocketMessage) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        console.warn('WebSocket is not connected. Message not sent:', message)
        return
      }

      try {
        wsRef.current.send(JSON.stringify(message))
      } catch (error) {
        console.error('Failed to send WebSocket message:', error)
      }
    },
    []
  )

  // Connect on mount if enabled
  useEffect(() => {
    if (enabled) {
      connect()
    }

    // Cleanup on unmount
    return () => {
      disconnect()
    }
  }, [enabled, connect, disconnect])

  return {
    isConnected,
    isReconnecting,
    reconnectAttempts,
    sendMessage,
    disconnect,
    connect,
  }
}
