import { createContext, useContext, useState, useEffect } from "react";

const ChatContext = createContext();

const createMessage = (role, content) => ({
  role,
  content,
  timestamp: new Date().toISOString(),
});

const DEFAULT_MESSAGES = {
  rag: [
    createMessage(
      "assistant",
      "🚀 Selamat datang di Smart Project Assistant!\n\nSaya bisa membantu Anda dengan progress, list, analisis, dan perbandingan project."
    ),
  ],
  project: [
    createMessage(
      "assistant",
      "📊 Selamat datang di Project Management!\n\nAnda bisa melihat daftar project, detail project, atau progress tertentu."
    ),
  ],
  todo: [
    createMessage(
      "assistant",
      "✅ Selamat datang di Task Assistant!\n\nAnda bisa membuat task baru, melihat task, atau menandai task selesai."
    ),
  ],
};

export const ChatProvider = ({ children }) => {
  const storageKey = "all_chat_messages";

  // Load sekali dari sessionStorage
  const [allMessages, setAllMessages] = useState(() => {
    const saved = sessionStorage.getItem(storageKey);
    try {
      const parsed = saved ? JSON.parse(saved) : null;
      return parsed && typeof parsed === "object"
        ? {
            rag: parsed.rag || DEFAULT_MESSAGES.rag,
            project: parsed.project || DEFAULT_MESSAGES.project,
            todo: parsed.todo || DEFAULT_MESSAGES.todo,
          }
        : DEFAULT_MESSAGES;
    } catch {
      return DEFAULT_MESSAGES;
    }
  });

  // Simpan setiap kali berubah ke sessionStorage
  useEffect(() => {
    sessionStorage.setItem(storageKey, JSON.stringify(allMessages));
  }, [allMessages]);

  const getMessages = (type) => allMessages[type] || [];
  const setMessages = (type, newMessages) => {
    setAllMessages((prev) => ({
      ...prev,
      [type]: Array.isArray(newMessages)
        ? newMessages.map((msg) => ({
            ...msg,
            role: msg.role || msg.type || "assistant",
            content: msg.content || "",
            timestamp: msg.timestamp || new Date().toISOString(),
          }))
        : [],
    }));
  };

  return (
    <ChatContext.Provider value={{ getMessages, setMessages }}>
      {children}
    </ChatContext.Provider>
  );
};

// Hook untuk konsumsi
export const useChat = (type) => {
  const { getMessages, setMessages } = useContext(ChatContext);
  if (!type) throw new Error("❌ useChat harus dipanggil dengan type");

  return {
    messages: getMessages(type),
    setMessages: (msgs) => setMessages(type, msgs),
  };
};
