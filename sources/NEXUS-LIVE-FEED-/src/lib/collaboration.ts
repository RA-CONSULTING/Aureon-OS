import { useEffect, useRef, useState } from 'react';

export interface Widget {
  id: string;
  title: string;
}

export interface UserPresence {
  id: string;
  name: string;
  color: string;
}

export interface CursorPosition {
  x: number;
  y: number;
}

export interface ChatMessage {
  id: string;
  userId: string;
  text: string;
  timestamp: number;
}

interface BaseMessage {
  type: string;
}

interface JoinMessage extends BaseMessage {
  type: 'join';
  user: UserPresence;
  session: string;
}

interface WidgetUpdateMessage extends BaseMessage {
  type: 'widget_update';
  widget: Widget;
}

interface CursorMessage extends BaseMessage {
  type: 'cursor';
  userId: string;
  cursor: CursorPosition;
}

interface ChatMessagePayload extends BaseMessage {
  type: 'chat';
  message: ChatMessage;
}

interface PresenceMessage extends BaseMessage {
  type: 'presence';
  users: UserPresence[];
}

type CollaborationMessage =
  | JoinMessage
  | WidgetUpdateMessage
  | CursorMessage
  | ChatMessagePayload
  | PresenceMessage;

/**
 * Simple collaboration hook using WebSockets.
 * Connects to a WebSocket endpoint and synchronises widgets, cursors and chat.
 * For conflict resolution the last write wins.
 */
export function useCollaboration(sessionId: string, user: UserPresence) {
  const [widgets, setWidgets] = useState<Widget[]>([]);
  const [users, setUsers] = useState<Record<string, UserPresence>>({});
  const [cursors, setCursors] = useState<Record<string, CursorPosition>>({});
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8080/collab/${sessionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      const join: JoinMessage = { type: 'join', user, session: sessionId };
      ws.send(JSON.stringify(join));
    };

    ws.onmessage = (event) => {
      try {
        const msg: CollaborationMessage = JSON.parse(event.data);
        switch (msg.type) {
          case 'presence':
            const presenceUsers: Record<string, UserPresence> = {};
            msg.users.forEach((u) => (presenceUsers[u.id] = u));
            setUsers(presenceUsers);
            break;
          case 'widget_update':
            setWidgets((prev) => {
              const exists = prev.find((w) => w.id === msg.widget.id);
              if (exists) {
                return prev.map((w) => (w.id === msg.widget.id ? msg.widget : w));
              }
              return [...prev, msg.widget];
            });
            break;
          case 'cursor':
            setCursors((prev) => ({ ...prev, [msg.userId]: msg.cursor }));
            break;
          case 'chat':
            setMessages((prev) => [...prev, msg.message]);
            break;
          default:
            break;
        }
      } catch {
        // ignore malformed messages
      }
    };

    return () => ws.close();
  }, [sessionId, user]);

  const updateWidget = (widget: Widget) => {
    setWidgets((prev) => {
      const exists = prev.find((w) => w.id === widget.id);
      if (exists) {
        return prev.map((w) => (w.id === widget.id ? widget : w));
      }
      return [...prev, widget];
    });
    const msg: WidgetUpdateMessage = { type: 'widget_update', widget };
    wsRef.current?.send(JSON.stringify(msg));
  };

  const sendCursor = (cursor: CursorPosition) => {
    const msg: CursorMessage = { type: 'cursor', userId: user.id, cursor };
    wsRef.current?.send(JSON.stringify(msg));
  };

  const sendChat = (text: string) => {
    const message: ChatMessage = {
      id: Math.random().toString(36).slice(2),
      userId: user.id,
      text,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, message]);
    const msg: ChatMessagePayload = { type: 'chat', message };
    wsRef.current?.send(JSON.stringify(msg));
  };

  return {
    widgets,
    users,
    cursors,
    messages,
    updateWidget,
    sendCursor,
    sendChat,
  };
}

export function randomColor() {
  const colors = ['red', 'green', 'blue', 'purple', 'orange'];
  return colors[Math.floor(Math.random() * colors.length)];
}

