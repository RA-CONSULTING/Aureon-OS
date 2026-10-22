import React, { useMemo, useState } from 'react';
import {
  ChatMessage,
  CursorPosition,
  randomColor,
  useCollaboration,
  UserPresence,
  Widget,
} from '../lib/collaboration';

// Simple dashboard builder demonstrating real-time collaboration.
const CollaborativeDashboardBuilder: React.FC = () => {
  // In a real app these would come from auth/session
  const user: UserPresence = useMemo(
    () => ({
      id: Math.random().toString(36).slice(2),
      name: `User-${Math.floor(Math.random() * 1000)}`,
      color: randomColor(),
    }),
    []
  );

  const {
    widgets,
    users,
    cursors,
    messages,
    updateWidget,
    sendCursor,
    sendChat,
  } = useCollaboration('default-session', user);

  const [chat, setChat] = useState('');

  const handleAddWidget = () => {
    const widget: Widget = {
      id: Math.random().toString(36).slice(2),
      title: 'New Widget',
    };
    updateWidget(widget);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = (e.target as HTMLDivElement).getBoundingClientRect();
    const cursor: CursorPosition = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
    sendCursor(cursor);
  };

  const handleChatSend = () => {
    if (chat.trim()) {
      sendChat(chat.trim());
      setChat('');
    }
  };

  return (
    <div className="flex h-[600px]">
      <div className="flex-1 border rounded mr-4 p-2 relative" onMouseMove={handleMouseMove}>
        <div className="mb-2 flex space-x-2">
          <button
            className="bg-blue-500 text-white px-3 py-1 rounded"
            onClick={handleAddWidget}
          >
            Add Widget
          </button>
          <div className="flex space-x-1 items-center">
            {Object.values(users).map((u) => (
              <span key={u.id} className="text-xs px-2 py-1 rounded" style={{ backgroundColor: u.color }}>
                {u.name}
              </span>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {widgets.map((w) => (
            <input
              key={w.id}
              className="border p-2"
              value={w.title}
              onChange={(e) => updateWidget({ ...w, title: e.target.value })}
            />
          ))}
        </div>
        {Object.entries(cursors).map(([id, pos]) => (
          <div
            key={id}
            className="absolute pointer-events-none text-xs"
            style={{ left: pos.x, top: pos.y, color: users[id]?.color }}
          >
            ▲
          </div>
        ))}
      </div>
      <div className="w-64 border rounded flex flex-col">
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {messages.map((m: ChatMessage) => (
            <div key={m.id} className="text-sm">
              <span className="font-bold" style={{ color: users[m.userId]?.color }}>
                {users[m.userId]?.name || 'anon'}:
              </span>{' '}
              {m.text}
            </div>
          ))}
        </div>
        <div className="p-2 border-t flex space-x-2">
          <input
            className="flex-1 border p-1 text-sm"
            value={chat}
            onChange={(e) => setChat(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleChatSend()}
          />
          <button className="text-sm px-2" onClick={handleChatSend}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

export default CollaborativeDashboardBuilder;

