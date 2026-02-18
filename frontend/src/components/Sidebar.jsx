import { Plus, MessageSquare, Trash2, Search } from 'lucide-react';

export default function Sidebar({ chats, deleteChat, onNewChat, onLogout }) {
  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col h-screen">
      {/* New Chat Button */}
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors text-black font-medium"
        >
          <Plus size={20} />
          New chat
        </button>
      </div>

      {/* Search Chats */}
      <div className="p-4 border-b border-gray-200">
        <div className="relative">
          <Search className="absolute left-3 top-3 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="Search chats..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent text-sm"
          />
        </div>
      </div>

      {/* Chat History */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        <div className="text-xs font-semibold text-gray-600 uppercase px-2 mb-3">Recent</div>
        {chats && chats.length > 0 ? (
          chats.map((chat) => (
            <div
              key={chat.id}
              className="p-3 rounded-lg cursor-pointer flex items-center justify-between group hover:bg-gray-100 transition-colors text-gray-800"
            >
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <MessageSquare size={16} className="flex-shrink-0" />
                <span className="text-sm truncate">{chat.title || 'Untitled Chat'}</span>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteChat(chat.id);
                }}
                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-300 rounded transition-all"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))
        ) : (
          <div className="text-sm text-gray-500 text-center py-8">No chats yet</div>
        )}
      </div>

      {/* Bottom Spacer */}
      <div className="p-4 border-t border-gray-200">
        <p className="text-xs text-gray-500 text-center">VisioNiX v1.0</p>
      </div>
    </div>
  );
}
