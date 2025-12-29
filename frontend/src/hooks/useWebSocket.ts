import { useEffect, useRef, useState, useCallback } from 'react'

export interface WebSocketMessage {
  type: string
  [key: string]: unknown
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
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isReconnecting, setIsReconnecting] = useState(false)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  const shouldReconnectRef = useRef(true)
  const [shouldConnect, setShouldConnect] = useState(enabled)

  // Store callbacks in refs to avoid recreating the WebSocket on callback changes
  const onMessageRef = useRef(onMessage)
  const onOpenRef = useRef(onOpen)
  const onCloseRef = useRef(onClose)
  const onErrorRef = useRef(onError)

  // Update callback refs when they change
  useEffect(() => {
    onMessageRef.current = onMessage
    onOpenRef.current = onOpen
    onCloseRef.current = onClose
    onErrorRef.current = onError
  }, [onMessage, onOpen, onClose, onError])

  // Main WebSocket connection effect
  useEffect(() => {
    if (!shouldConnect || !enabled) {
      return
    }

    // Don't connect if already connected
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    let ws: WebSocket
    let isCancelled = false

    const createConnection = () => {
      try {
        ws = new WebSocket(url)
        wsRef.current = ws

        ws.onopen = () => {
          if (isCancelled) return
          console.log('WebSocket connected:', url)
          setIsConnected(true)
          setIsReconnecting(false)
          setReconnectAttempts(0)
          shouldReconnectRef.current = true
          onOpenRef.current?.()
        }

        ws.onmessage = (event) => {
          if (isCancelled) return
          try {
            const message = JSON.parse(event.data) as WebSocketMessage
            onMessageRef.current?.(message)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        ws.onerror = (error) => {
          if (isCancelled) return
          console.error('WebSocket error:', error)
          onErrorRef.current?.(error)
        }

        ws.onclose = () => {
          if (isCancelled) return
          console.log('WebSocket disconnected:', url)
          setIsConnected(false)
          onCloseRef.current?.()

          // Attempt reconnection if not manually disconnected
          setReconnectAttempts((currentAttempts) => {
            if (shouldReconnectRef.current && currentAttempts < maxReconnectAttempts) {
              setIsReconnecting(true)
              const nextAttempt = currentAttempts + 1

              // Exponential backoff: 3s, 6s, 12s, 24s, 48s
              const backoffDelay = Math.min(
                reconnectInterval * Math.pow(2, currentAttempts),
                30000 // Max 30 seconds
              )

              console.log(
                `WebSocket reconnecting in ${backoffDelay}ms (attempt ${nextAttempt}/${maxReconnectAttempts})`
              )

              reconnectTimeoutRef.current = setTimeout(() => {
                if (!isCancelled) {
                  createConnection()
                }
              }, backoffDelay)

              return nextAttempt
            } else if (currentAttempts >= maxReconnectAttempts) {
              console.error('WebSocket max reconnect attempts reached')
              setIsReconnecting(false)
            }
            return currentAttempts
          })
        }
      } catch (error) {
        console.error('Failed to create WebSocket connection:', error)
        setIsConnected(false)
      }
    }

    createConnection()

    // Cleanup function
    return () => {
      isCancelled = true
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
      if (ws) {
        shouldReconnectRef.current = false
        ws.close()
      }
    }
  }, [url, enabled, shouldConnect, reconnectInterval, maxReconnectAttempts])

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false
    setShouldConnect(false)
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

  const connect = useCallback(() => {
    shouldReconnectRef.current = true
    setReconnectAttempts(0)
    setShouldConnect(true)
  }, [])

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket is not connected. Message not sent:', message)
      return
    }

    try {
      wsRef.current.send(JSON.stringify(message))
    } catch (error) {
      console.error('Failed to send WebSocket message:', error)
    }
  }, [])

  return {
    isConnected,
    isReconnecting,
    reconnectAttempts,
    sendMessage,
    disconnect,
    connect,
  }
}
