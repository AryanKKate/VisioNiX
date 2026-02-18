import { useState, useRef, useEffect, useMemo } from 'react';
import { Send } from 'lucide-react';
import Message from './Message';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000';

function mapMessage(raw) {
  const imageDataUrl = raw.image_data
    ? `data:${raw.image_mime_type || 'image/png'};base64,${raw.image_data}`
    : null;

  return {
    id: raw.id,
    type: raw.role,
    content: raw.content,
    timestamp: raw.created_at,
    imageDataUrl,
    imageName: raw.image_name,
  };
}

export default function ChatWindow({ model, roomId, onRoomRefreshNeeded }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);

  const token = useMemo(() => localStorage.getItem('token'), []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const fetchMessages = async () => {
      if (!roomId) {
        setMessages([]);
        return;
      }

      setError('');
      try {
        const response = await fetch(`${apiBaseUrl}/chat/rooms/${roomId}/messages`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error || 'Failed to load chat messages');
        }

        setMessages((data.messages || []).map(mapMessage));
      } catch (err) {
        setError(err.message || 'Failed to load chat messages');
      }
    };

    fetchMessages();
  }, [roomId, token]);

  const handleSendMessage = async (e) => {
    e.preventDefault();

    if (!input.trim() || !roomId || loading) {
      return;
    }

    setLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('prompt', input.trim());
      formData.append('model', model === 'normal' ? 'qwen3-vl:8b' : model);
      if (selectedFile) {
        formData.append('image', selectedFile);
      }

      const response = await fetch(`${apiBaseUrl}/chat/rooms/${roomId}/messages`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to send message');
      }

      const nextMessages = [data.user_message, data.assistant_message].filter(Boolean).map(mapMessage);
      setMessages((prev) => [...prev, ...nextMessages]);
      setInput('');
      setSelectedFile(null);
      onRoomRefreshNeeded?.();
    } catch (err) {
      setError(err.message || 'Failed to send message');
    } finally {
      setLoading(false);
    }
  };

  const isEmptyState = messages.length === 0;

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-primary">
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {!roomId ? (
          <div className="h-full flex items-center justify-center text-text-secondary">Create a new chat to begin.</div>
        ) : isEmptyState ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <h2 className="text-4xl font-bold text-light mb-2">How can I help you?</h2>
              <p className="text-text-secondary">Ask anything and optionally attach an image for context.</p>
            </div>
          </div>
        ) : (
          messages.map((msg) => <Message key={msg.id} message={msg} />)
        )}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface rounded-lg px-4 py-3 max-w-2xl">
              <div className="flex gap-2">
                <div className="w-2 h-2 bg-text-secondary rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-text-secondary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-text-secondary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}

        {error && <p className="text-sm text-red-400">{error}</p>}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-border p-6 bg-primary">
        <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto">
          <div className="flex gap-3 items-center">
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              className="text-sm text-light file:mr-3 file:px-3 file:py-2 file:rounded-lg file:border-0 file:bg-surface-light file:text-light"
              disabled={loading || !roomId}
            />
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything"
              className="flex-1 px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-surface-light focus:border-transparent bg-secondary text-light placeholder-text-secondary"
              disabled={loading || !roomId}
            />
            <button
              type="submit"
              disabled={loading || !input.trim() || !roomId}
              className="p-3 bg-surface-light text-light rounded-lg hover:bg-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send size={20} />
            </button>
          </div>
          {selectedFile && <p className="mt-2 text-xs text-text-secondary">Ready: {selectedFile.name}</p>}
        </form>
      </div>
    </div>
  );
}
