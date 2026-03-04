import { useState, useRef, useEffect, useCallback } from "react";
import { Send } from "lucide-react";

import Message from "./Message";
import { useExtraction } from "../hooks/useExtraction";

const DEFAULT_MODEL_ID = "__default__";

const getWelcomeMessage = () => ({
  id: "bot-welcome",
  type: "bot",
  content: "How can I help you today?",
  timestamp: new Date(),
});

const createMessageId = () =>
  `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const isJwt = (value) =>
  typeof value === "string" && value.split(".").length === 3;

export default function ChatWindow({
  currentChatId,
  selectedModelId = DEFAULT_MODEL_ID,
}) {
  const apiBaseUrl =
    import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000";

  const { addExtraction } = useExtraction();

  const [messages, setMessages] = useState([getWelcomeMessage()]);
  const [input, setInput] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const messagesEndRef = useRef(null);
  const previewUrlsRef = useRef([]);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const mapServerMessage = useCallback((message) => {
    const isUser = message?.role === "user";
    const mime = message?.image_mime_type || "image/jpeg";

    const imageUrl = message?.image_data
      ? `data:${mime};base64,${message.image_data}`
      : undefined;

    return {
      id: message?.id || createMessageId(),
      type: isUser ? "user" : "bot",
      content: message?.content || "",
      imageUrl,
      timestamp: message?.created_at ? new Date(message.created_at) : new Date(),
    };
  }, []);

  const loadMessages = useCallback(async () => {
    const token = localStorage.getItem("token");

    if (!token || !currentChatId) {
      setMessages([getWelcomeMessage()]);
      return;
    }

    if (!isJwt(token)) {
      localStorage.removeItem("token");
      setError("Session invalid. Please log in again.");
      setMessages([getWelcomeMessage()]);
      return;
    }

    try {
      const response = await fetch(
        `${apiBaseUrl}/chat/rooms/${currentChatId}/messages`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Failed to load messages");
      }

      const rows = data.messages || [];
      setMessages(
        rows.length === 0 ? [getWelcomeMessage()] : rows.map(mapServerMessage)
      );
    } catch (err) {
      setError(err.message);
      setMessages([getWelcomeMessage()]);
    }
  }, [apiBaseUrl, currentChatId, mapServerMessage]);

  useEffect(() => {
    loadMessages();
  }, [loadMessages]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    return () => {
      previewUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
      previewUrlsRef.current = [];
    };
  }, []);

  const handleSendMessage = async (e) => {
    e.preventDefault();

    const token = localStorage.getItem("token");
    if (!input.trim() || !currentChatId) return;

    if (!isJwt(token)) {
      localStorage.removeItem("token");
      setError("Session invalid. Please log in again.");
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
      type: "user",
      content: prompt,
      imageUrl: imagePreviewUrl,
      timestamp: new Date(),
    };

    setMessages((prev) =>
      prev.length === 1 && prev[0].id === "bot-welcome"
        ? [userMessage]
        : [...prev, userMessage]
    );

    setInput("");
    setLoading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("prompt", prompt);

      if (selectedModelId && selectedModelId !== DEFAULT_MODEL_ID) {
        formData.append("model_id", selectedModelId);
      }

      if (fileToSend) {
        formData.append("image", fileToSend);
      }

      const response = await fetch(
        `${apiBaseUrl}/chat/rooms/${currentChatId}/messages`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        }
      );
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Failed to send message");
      }

      if (data.assistant_message) {
        setMessages((prev) => [...prev, mapServerMessage(data.assistant_message)]);
      }

      if (data.extraction) {
        addExtraction(data.extraction);
      }

      setSelectedFile(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-primary">
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((msg) => (
          <Message key={msg.id} message={msg} />
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface rounded-lg px-4 py-3">Thinking...</div>
          </div>
        )}

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-border p-6 bg-primary">
        <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto">
          <div className="mb-3 flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              disabled={loading}
              className="hidden"
            />

            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={loading}
              className="px-3 py-2 border border-border rounded-lg bg-secondary text-light hover:bg-hover disabled:opacity-50"
            >
              {selectedFile ? "Change Image" : "Choose Image"}
            </button>

            <span
              className={`text-xs max-w-[220px] truncate ${
                selectedFile ? "text-light" : "text-text-secondary"
              }`}
              title={selectedFile?.name || "No file chosen"}
            >
              {selectedFile ? selectedFile.name : "No file chosen"}
            </span>

            {selectedFile && (
              <button
                type="button"
                onClick={() => setSelectedFile(null)}
                disabled={loading}
                className="px-2 py-1 text-xs border border-border rounded-md text-text-secondary hover:text-light hover:bg-hover disabled:opacity-50"
              >
                Remove
              </button>
            )}
          </div>

          <div className="flex gap-3 items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything"
              className="flex-1 px-4 py-3 border border-border rounded-lg bg-secondary text-light"
              disabled={loading}
            />

            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="p-3 bg-surface-light text-light rounded-lg"
            >
              <Send size={20} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
