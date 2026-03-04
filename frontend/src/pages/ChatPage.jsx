import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, MessageSquare, Trash2, LogOut, Image, ChevronDown, Search, SlidersHorizontal } from 'lucide-react';
import { jwtDecode } from 'jwt-decode';

import { useAuth } from '../hooks/useAuth';
import ChatWindow from '../components/ChatWindow';
import { supabase } from '../components/supabase';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000';
const isJwt = (value) => typeof value === 'string' && value.split('.').length === 3;
const DEFAULT_MODEL = {
  id: '__default__',
  name: 'VisioNiX 1.0',
  is_virtual: true,
};

export default function ChatPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const token = localStorage.getItem('token');

  const [showModelDropdown, setShowModelDropdown] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [chats, setChats] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [models, setModels] = useState([DEFAULT_MODEL]);
  const [selectedModelId, setSelectedModelId] = useState(DEFAULT_MODEL.id);

  useEffect(() => {
    if (!user) {
      navigate('/');
    }
  }, [user, navigate]);

  const loadRooms = useCallback(async () => {
    if (!token) {
      setChats([]);
      setCurrentChatId(null);
      return;
    }
    if (!isJwt(token)) {
      localStorage.removeItem('token');
      logout();
      navigate('/');
      return;
    }

    try {
      const response = await fetch(`${apiBaseUrl}/chat/rooms`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch rooms');
      }

      const rooms = data.rooms || [];
      setChats(rooms);
      setCurrentChatId((prev) => {
        if (prev && rooms.some((room) => room.id === prev)) {
          return prev;
        }
        return rooms[0]?.id || null;
      });
    } catch {
      setChats([]);
      setCurrentChatId(null);
    }
  }, [navigate, logout, token]);

  useEffect(() => {
    loadRooms();
  }, [loadRooms]);

  const loadModels = useCallback(async () => {
    try {
      setModelsLoading(true);

      if (!token || !isJwt(token)) {
        setModels([DEFAULT_MODEL]);
        setSelectedModelId(DEFAULT_MODEL.id);
        return;
      }

      const decoded = jwtDecode(token);
      const userId = decoded.sub;
      if (!userId) {
        setModels([DEFAULT_MODEL]);
        setSelectedModelId(DEFAULT_MODEL.id);
        return;
      }

      const { data, error } = await supabase
        .from('models')
        .select('*')
        .or(`owner_id.eq.${userId},is_default.eq.true`)
        .order('created_at', { ascending: true });

      if (error) throw error;

      const combinedModels = [DEFAULT_MODEL, ...(data || [])];
      setModels(combinedModels);
      setSelectedModelId((prev) =>
        combinedModels.some((model) => model.id === prev) ? prev : DEFAULT_MODEL.id
      );
    } catch (error) {
      console.error('Load models failed:', error);
      setModels([DEFAULT_MODEL]);
      setSelectedModelId(DEFAULT_MODEL.id);
    } finally {
      setModelsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleNewChat = async () => {
    if (!token || !isJwt(token)) {
      localStorage.removeItem('token');
      logout();
      navigate('/');
      return;
    }
    try {
      const response = await fetch(`${apiBaseUrl}/chat/rooms`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ title: 'New Chat' }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to create chat');
      }

      const room = data.room;
      if (!room) return;
      setChats((prev) => [room, ...prev]);
      setCurrentChatId(room.id);
    } catch (error) {
      console.error(error);
    }
  };

  const handleDeleteChat = async (id) => {
    if (!token || !isJwt(token)) {
      localStorage.removeItem('token');
      logout();
      navigate('/');
      return;
    }
    try {
      const response = await fetch(`${apiBaseUrl}/chat/rooms/${id}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to delete chat');
      }

      setChats((prev) => {
        const updated = prev.filter((chat) => chat.id !== id);
        if (currentChatId === id) {
          setCurrentChatId(updated.length > 0 ? updated[0].id : null);
        }
        return updated;
      });
    } catch (error) {
      console.error(error);
    }
  };

  const currentModel = models.find((m) => m.id === selectedModelId);

  const filteredChats = chats.filter((chat) =>
    (chat.title || 'Untitled Chat').toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (!user) {
    return null;
  }

  return (
    <div className="flex h-screen bg-primary">
      <div className="w-64 bg-secondary border-r border-border flex flex-col h-screen">
        <div className="p-4 border-b border-border">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-border rounded-lg hover:bg-hover transition-colors text-light font-medium"
          >
            <Plus size={20} />
            New chat
          </button>
        </div>

        <div className="p-4 border-b border-border">
          <div className="relative">
            <Search className="absolute left-3 top-3 text-text-secondary" size={18} />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search chats..."
              className="w-full pl-10 pr-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-surface-light focus:border-transparent text-sm bg-primary text-light placeholder-text-secondary"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          <div className="text-xs font-semibold text-text-secondary uppercase px-2 mb-3">Recent</div>
          {filteredChats.length > 0 ? (
            filteredChats.map((chat) => (
              <div
                key={chat.id}
                onClick={() => setCurrentChatId(chat.id)}
                className={`p-3 rounded-lg cursor-pointer flex items-center justify-between group transition-colors text-light ${
                  currentChatId === chat.id ? 'bg-hover' : 'hover:bg-hover'
                }`}
              >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <MessageSquare size={16} className="flex-shrink-0" />
                  <span className="text-sm truncate">{chat.title || 'Untitled Chat'}</span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteChat(chat.id);
                  }}
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

      <div className="flex-1 flex flex-col bg-primary">
        <div className="border-b border-border px-6 py-4 flex items-center justify-between bg-primary">
          <div />

          <div className="relative">
            <button
              onClick={() => setShowModelDropdown(!showModelDropdown)}
              className="flex items-center gap-2 px-4 py-2 border border-border rounded-lg hover:bg-hover transition-colors text-light"
            >
              <span className="font-medium">
                {modelsLoading ? 'Loading models...' : currentModel?.name || 'Select Model'}
              </span>
              <ChevronDown size={18} className="text-text-secondary" />
            </button>

            {showModelDropdown && (
              <div className="absolute left-1/2 -translate-x-1/2 mt-2 w-56 max-h-64 overflow-y-auto bg-secondary border border-border rounded-lg shadow-lg z-50">
                {models.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => {
                      setSelectedModelId(model.id);
                      setShowModelDropdown(false);
                    }}
                    className={`w-full px-4 py-2 text-left hover:bg-hover transition-colors border-b border-border last:border-b-0 text-sm text-light ${
                      selectedModelId === model.id ? 'bg-hover font-semibold' : ''
                    }`}
                  >
                    {model.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="flex items-center gap-4 -mr-1 md:-mr-2">
            <button
              onClick={() => navigate('/finetune')}
              className="p-2.5 hover:bg-hover rounded-lg transition-colors"
              title="Fine-tune Models"
            >
              <SlidersHorizontal size={24} className="text-light" />
            </button>
            <button
              onClick={() => navigate('/extractions')}
              className="p-2.5 hover:bg-hover rounded-lg transition-colors"
              title="View Extractions"
            >
              <Image size={24} className="text-light" />
            </button>
          </div>
        </div>

        <ChatWindow currentChatId={currentChatId} selectedModelId={selectedModelId} />
      </div>
    </div>
  );
}
