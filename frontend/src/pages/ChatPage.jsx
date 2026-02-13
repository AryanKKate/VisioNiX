import { useAuth } from '../hooks/useAuth';
import { useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { Plus, MessageSquare, Trash2, LogOut, Image, ChevronDown, Search } from 'lucide-react';
import ChatWindow from '../components/ChatWindow';

export default function ChatPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [selectedModel, setSelectedModel] = useState('normal');
  const [showModelDropdown, setShowModelDropdown] = useState(false);
  const [chats, setChats] = useState([]);

  useEffect(() => {
    if (!user) {
      navigate('/');
    }
  }, [user, navigate]);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleNewChat = () => {
    const newChat = {
      id: Date.now().toString(),
      title: 'New Chat',
      timestamp: new Date(),
    };
    setChats(prev => [newChat, ...prev]);
  };

  const handleDeleteChat = (id) => {
    setChats(prev => prev.filter(chat => chat.id !== id));
  };

  const models = [
    { id: 'normal', label: 'Normal' },
    { id: 'yolo', label: 'YOLO' },
    { id: 'clip', label: 'CLIP' },
    { id: 'custom', label: 'Custom' },
  ];

  const currentModel = models.find(m => m.id === selectedModel);

  if (!user) {
    return null;
  }

  return (
    <div className="flex h-screen bg-primary">
      {/* Left Sidebar - ChatGPT Style */}
      <div className="w-64 bg-secondary border-r border-border flex flex-col h-screen">
        {/* New Chat Button */}
        <div className="p-4 border-b border-border">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-border rounded-lg hover:bg-hover transition-colors text-light font-medium"
          >
            <Plus size={20} />
            New chat
          </button>
        </div>

        {/* Search Chats */}
        <div className="p-4 border-b border-border">
          <div className="relative">
            <Search className="absolute left-3 top-3 text-text-secondary" size={18} />
            <input
              type="text"
              placeholder="Search chats..."
              className="w-full pl-10 pr-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-surface-light focus:border-transparent text-sm bg-primary text-light placeholder-text-secondary"
            />
          </div>
        </div>

        {/* Chat History */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          <div className="text-xs font-semibold text-text-secondary uppercase px-2 mb-3">Recent</div>
          {chats && chats.length > 0 ? (
            chats.map((chat) => (
              <div
                key={chat.id}
                className="p-3 rounded-lg cursor-pointer flex items-center justify-between group hover:bg-hover transition-colors text-light"
              >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <MessageSquare size={16} className="flex-shrink-0" />
                  <span className="text-sm truncate">{chat.title}</span>
                </div>
                <button
                  onClick={() => handleDeleteChat(chat.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-border rounded transition-all"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))
          ) : (
            <div className="text-sm text-text-secondary text-center py-8">No chats yet</div>
          )}
        </div>

        {/* User Section */}
        <div className="p-4 border-t border-border">
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 text-light hover:bg-hover rounded-lg transition-colors font-medium text-sm"
          >
            <LogOut size={18} />
            Logout
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col bg-primary">
        {/* Header with Model Dropdown */}
        <div className="border-b border-border px-6 py-4 flex items-center justify-between bg-primary">
          <div></div>

          {/* Model Dropdown - Center */}
          <div className="relative">
            <button
              onClick={() => setShowModelDropdown(!showModelDropdown)}
              className="flex items-center gap-2 px-4 py-2 border border-border rounded-lg hover:bg-hover transition-colors text-light"
            >
              <span className="font-medium">{currentModel?.label}</span>
              <ChevronDown size={18} className="text-text-secondary" />
            </button>

            {showModelDropdown && (
              <div className="absolute left-1/2 -translate-x-1/2 mt-2 w-40 bg-secondary border border-border rounded-lg shadow-lg z-50">
                {models.map(model => (
                  <button
                    key={model.id}
                    onClick={() => {
                      setSelectedModel(model.id);
                      setShowModelDropdown(false);
                    }}
                    className={`w-full px-4 py-2 text-left hover:bg-hover transition-colors border-b border-border last:border-b-0 text-sm text-light ${
                      selectedModel === model.id ? 'bg-hover font-semibold' : ''
                    }`}
                  >
                    {model.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Right Icons */}
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/extractions')}
              className="p-2 hover:bg-hover rounded-lg transition-colors"
              title="View Extractions"
            >
              <Image size={20} className="text-light" />
            </button>
          </div>
        </div>

        {/* Chat Window */}
        <ChatWindow model={selectedModel} />
      </div>
    </div>
  );
}
