import { createContext, useState, useCallback } from 'react';

export const ChatContext = createContext();

export function ChatProvider({ children }) {
  const [chats, setChats] = useState([
    {
      id: '1',
      title: 'Sample Chat 1',
      timestamp: new Date(Date.now() - 3600000),
      messages: [
        { id: '1', role: 'user', content: 'Hello, can you help me?' },
        { id: '2', role: 'assistant', content: 'Of course! I\'m here to help.' }
      ]
    }
  ]);
  
  const [currentChatId, setCurrentChatId] = useState('1');
  const [selectedModel, setSelectedModel] = useState('normal');

  const getCurrentChat = useCallback(() => {
    return chats.find(chat => chat.id === currentChatId) || null;
  }, [chats, currentChatId]);

  const createNewChat = useCallback(() => {
    const newChat = {
      id: Date.now().toString(),
      title: 'New Chat',
      timestamp: new Date(),
      messages: []
    };
    setChats(prev => [newChat, ...prev]);
    setCurrentChatId(newChat.id);
    return newChat;
  }, []);

  const addMessage = useCallback((chatId, message) => {
    setChats(prev => prev.map(chat => {
      if (chat.id === chatId) {
        return {
          ...chat,
          messages: [...chat.messages, message]
        };
      }
      return chat;
    }));
  }, []);

  const updateChatTitle = useCallback((chatId, title) => {
    setChats(prev => prev.map(chat => {
      if (chat.id === chatId) {
        return { ...chat, title };
      }
      return chat;
    }));
  }, []);

  const deleteChat = useCallback((chatId) => {
    setChats(prev => prev.filter(chat => chat.id !== chatId));
    if (currentChatId === chatId) {
      setCurrentChatId(prev => {
        const remaining = chats.filter(c => c.id !== chatId);
        return remaining.length > 0 ? remaining[0].id : null;
      });
    }
  }, [chats, currentChatId]);

  return (
    <ChatContext.Provider value={{
      chats,
      currentChatId,
      selectedModel,
      getCurrentChat,
      createNewChat,
      addMessage,
      updateChatTitle,
      deleteChat,
      setCurrentChatId,
      setSelectedModel
    }}>
      {children}
    </ChatContext.Provider>
  );
}
