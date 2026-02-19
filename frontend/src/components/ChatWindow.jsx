import { useState, useRef, useEffect, useCallback } from 'react';
import { Send } from 'lucide-react';
import Message from './Message';

const getWelcomeMessage = () => ({
  id: 'bot-welcome',
  type: 'bot',
  content: 'How can I help you today?',
  timestamp: new Date(),
});

const createMessageId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const resolveOllamaModel = (uiModel) => {
  const modelMap = {
    normal: 'qwen3-vl:8b',
    yolo: 'qwen3-vl:8b',
    clip: 'qwen3-vl:8b',
    custom: 'qwen3-vl:8b',
  };
  return modelMap[uiModel] || 'qwen3-vl:8b';
};

export default function ChatWindow({ model, currentChatId }) {
  const token = localStorage.getItem('token');
  const [messages, setMessages] = useState([getWelcomeMessage()]);
  const [input, setInput] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);
  const previewUrlsRef = useRef([]);
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000';

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const mapServerMessage = useCallback((message) => {
    const role = message?.role === 'user' ? 'user' : 'bot';
    const mime = message?.image_mime_type || 'image/jpeg';
    const imageUrl = message?.image_data ? `data:${mime};base64,${message.image_data}` : undefined;
    return {
      id: message?.id || createMessageId(),
      type: role,
      content: message?.content || '',
      imageUrl,
      timestamp: message?.created_at ? new Date(message.created_at) : new Date(),
    };
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    previewUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    previewUrlsRef.current = [];
    setMessages([getWelcomeMessage()]);
    setInput('');
    setSelectedFile(null);
  }, [currentChatId]);

  const loadMessages = useCallback(async () => {
    if (!token || !currentChatId) {
      setMessages([getWelcomeMessage()]);
      return;
    }
    try {
      const response = await fetch(`${apiBaseUrl}/chat/rooms/${currentChatId}/messages`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to load messages');
      }
      const rows = data.messages || [];
      if (rows.length === 0) {
        setMessages([getWelcomeMessage()]);
      } else {
        setMessages(rows.map(mapServerMessage));
      }
    } catch (err) {
      setError(err.message || 'Failed to load messages');
      setMessages([getWelcomeMessage()]);
    }
  }, [apiBaseUrl, currentChatId, mapServerMessage, token]);

  useEffect(() => {
    loadMessages();
  }, [loadMessages]);

  useEffect(() => () => {
    previewUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    previewUrlsRef.current = [];
  }, []);

  const handleSendMessage = async (e) => {
    e.preventDefault();

    if (!input.trim()) return;
    if (!currentChatId) {
      return;
    }

    const prompt = input.trim();
    const fileToSend = selectedFile;
    let imagePreviewUrl;
    if (fileToSend) {
      imagePreviewUrl = URL.createObjectURL(fileToSend);
      previewUrlsRef.current.push(imagePreviewUrl);
    }

    const userMessage = {
      id: createMessageId(),
      type: 'user',
      content: prompt,
      imageUrl: imagePreviewUrl,
      timestamp: new Date(),
    };
    setMessages((prev) => {
      const withoutWelcome =
        prev.length === 1 && prev[0].id === 'bot-welcome' ? [] : prev;
      return [...withoutWelcome, userMessage];
    });
    setInput('');
    setLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('prompt', prompt);
      formData.append('model', resolveOllamaModel(model));
      if (fileToSend) {
        formData.append('image', fileToSend);
      }

      const response = await fetch(`${apiBaseUrl}/chat/rooms/${currentChatId}/messages`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || 'Failed to send message');
      }

      const assistantMessage = data.assistant_message ? mapServerMessage(data.assistant_message) : null;
      setMessages((prev) => [
        ...prev,
        ...(assistantMessage ? [assistantMessage] : []),
      ]);
      setSelectedFile(null);
    } catch (err) {
      const errorMessage = {
        id: createMessageId(),
        type: 'bot',
        content: `Message send failed: ${err.message}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const isEmptyState = messages.length === 0;

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-primary">
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {!currentChatId ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <h2 className="text-4xl font-bold text-light mb-2">How can I help you today?</h2>
              <p className="text-text-secondary">Create a new chat to begin.</p>
            </div>
          </div>
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
                disabled={loading || !currentChatId}
              />
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything"
              className="flex-1 px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-surface-light focus:border-transparent bg-secondary text-light placeholder-text-secondary"
              disabled={loading || !currentChatId}
            />
            <button
              type="submit"
              disabled={loading || !input.trim() || !currentChatId}
              className="p-3 bg-surface-light text-light rounded-lg hover:bg-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send size={20} />
            </button>
          </div>
          {selectedFile && (
            <p className="mt-2 text-xs text-text-secondary">
              Ready: {selectedFile.name}
            </p>
          )}
        </form>
      </div>
    </div>
  );
}
