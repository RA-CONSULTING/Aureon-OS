
import React, { useRef, useEffect } from 'react';
import { marked } from 'marked';
import { ChatMessage } from './types';

interface ChatPanelProps {
  messages: ChatMessage[];
  onSendMessage: () => void;
  isLoading: boolean;
  isThinkingMode: boolean;
  onToggleThinkingMode: (enabled: boolean) => void;
  isRecording: boolean;
  onToggleRecording: () => void;
  inputValue: string;
  onInputChange: (value: string) => void;
}

const ChatPanel: React.FC<ChatPanelProps> = ({ 
  messages, 
  onSendMessage, 
  isLoading, 
  isThinkingMode, 
  onToggleThinkingMode,
  isRecording,
  onToggleRecording,
  inputValue,
  onInputChange
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && !isLoading) {
      onSendMessage();
    }
  };

  const renderMessageContent = (content: string) => {
    const sanitizedHtml = marked.parse(content, { gfm: true, breaks: true });
    return { __html: sanitizedHtml as string };
  };

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg shadow-lg flex flex-col h-[60vh] max-h-[700px]">
      <div className="p-4 border-b border-gray-700">
        <div className="flex justify-between items-center">
            <div>
                <h3 className="text-xl font-semibold text-gray-200">Chat with AUREON</h3>
                <p className="text-sm text-gray-400">Request tactical analysis or system status reports.</p>
            </div>
             <div className="flex items-center space-x-2 group relative">
                <label htmlFor="thinking-mode" className="text-sm font-medium text-gray-300 cursor-pointer">Deep Analysis</label>
                <button
                    role="switch"
                    aria-checked={isThinkingMode}
                    id="thinking-mode"
                    onClick={() => onToggleThinkingMode(!isThinkingMode)}
                    className={`${isThinkingMode ? 'bg-sky-500' : 'bg-gray-600'} relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-gray-800`}
                >
                    <span className={`${isThinkingMode ? 'translate-x-6' : 'translate-x-1'} inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}/>
                </button>
                <div className="absolute bottom-full mb-2 w-64 p-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none">
                    Enable for deeper, more comprehensive answers. AUREON will use more processing time to correlate data across multiple domains.
                </div>
            </div>
        </div>
      </div>
      <div className="flex-grow p-4 overflow-y-auto space-y-4">
        {messages.map((msg, index) => (
          <div key={index} className={`flex items-start gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
            {msg.role === 'model' && (
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center flex-shrink-0">
                 <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 12h14M12 5l7 7-7 7"></path></svg>
              </div>
            )}
            <div className={`max-w-xl rounded-lg ${msg.role === 'user' ? 'bg-sky-800' : 'bg-gray-700'}`}>
              <div
                className="chat-content text-sm p-3"
                dangerouslySetInnerHTML={renderMessageContent(msg.content)}
              />
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-600 px-3 pb-2">
                  <h4 className="text-xs font-semibold text-gray-400 mb-1">Sources:</h4>
                  <ol className="list-decimal list-inside space-y-1">
                    {msg.sources.map((source, i) => (
                      <li key={i} className="text-xs truncate">
                        <a 
                          href={source.uri} 
                          target="_blank" 
                          rel="noopener noreferrer" 
                          title={source.uri} 
                          className="text-sky-400 hover:text-sky-300 hover:underline"
                        >
                          {source.title}
                        </a>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          </div>
        ))}
         {isLoading && messages[messages.length - 1]?.role === 'model' && (
            <div className="flex items-start gap-3">
                 <div className="w-8 h-8 rounded-full bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center flex-shrink-0">
                     <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 12h14M12 5l7 7-7 7"></path></svg>
                </div>
                <div className="max-w-xl p-3 rounded-lg bg-gray-700">
                    <div className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-sky-400 rounded-full animate-pulse"></div>
                        <div className="w-2 h-2 bg-sky-400 rounded-full animate-pulse [animation-delay:0.2s]"></div>
                        <div className="w-2 h-2 bg-sky-400 rounded-full animate-pulse [animation-delay:0.4s]"></div>
                    </div>
                </div>
            </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <form onSubmit={handleSend} className="p-4 border-t border-gray-700 flex items-center gap-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder={isRecording ? "Listening..." : "Enter tactical query..."}
          className="w-full bg-gray-900 border border-gray-600 rounded-full py-2 px-4 focus:outline-none focus:ring-2 focus:ring-sky-500"
          disabled={isLoading || isRecording}
        />
        <button
          type="button"
          onClick={onToggleRecording}
          disabled={isLoading}
          className={`p-2 rounded-full transition-colors ${
            isRecording 
              ? 'bg-red-600 hover:bg-red-700 animate-pulse' 
              : 'bg-gray-600 hover:bg-gray-500'
          } disabled:bg-gray-700 disabled:cursor-not-allowed text-white`}
          aria-label={isRecording ? "Stop recording" : "Start recording"}
        >
          {isRecording ? (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M5 5a1 1 0 011-1h8a1 1 0 011 1v8a1 1 0 01-1 1H6a1 1 0 01-1-1V5z" clipRule="evenodd" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          )}
        </button>
        <button
          type="submit"
          disabled={isLoading || !inputValue.trim() || isRecording}
          className="bg-sky-600 hover:bg-sky-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-bold p-2 rounded-full transition-colors"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 10l7-7m0 0l7 7m-7-7v18"></path></svg>
        </button>
      </form>
    </div>
  );
};

export default ChatPanel;
