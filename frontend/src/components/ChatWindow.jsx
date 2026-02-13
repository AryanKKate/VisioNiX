import { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import Message from './Message';

export default function ChatWindow({ model }) {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      content: 'How can I help you today?',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    if (!input.trim()) return;

    const userMessage = {
      id: messages.length + 1,
      type: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    // Simulate bot response
    setTimeout(() => {
      const botMessage = {
        id: messages.length + 2,
        type: 'bot',
        content: `Analyzing with ${model} model...`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, botMessage]);
      setLoading(false);
    }, 1000);
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-primary">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 1 && messages[0].type === 'bot' && messages[0].content === 'How can I help you today?' ? (
          // Empty State
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <h2 className="text-4xl font-bold text-light mb-2">How can I help you?</h2>
              <p className="text-text-secondary">Ask me anything about image analysis, vision tasks, or upload an image to analyze.</p>
            </div>
          </div>
        ) : (
          messages.map(msg => (
            <Message key={msg.id} message={msg} />
          ))
        )}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface rounded-lg px-4 py-3 max-w-2xl">
              <div className="flex gap-2">
                <div className="w-2 h-2 bg-text-secondary rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-text-secondary rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                <div className="w-2 h-2 bg-text-secondary rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-border p-6 bg-primary">
        <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything"
              className="flex-1 px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-surface-light focus:border-transparent bg-secondary text-light placeholder-text-secondary"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="p-3 bg-surface-light text-light rounded-lg hover:bg-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send size={20} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
