import { useEffect, useMemo, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import Avatar from "../components/Avatar";
import ChatInput from "../components/ChatInput";
import MessageBubble from "../components/MessageBubble";
import TypingIndicator from "../components/TypingIndicator";
import { useAuthStore } from "../store/authStore";
import { useChatStore } from "../store/chatStore";
import { useProfileStore } from "../store/profileStore";

export default function ChatPage() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const clearAuth = useAuthStore((state) => state.clear);

  const conversations = useChatStore((state) => state.conversations);
  const conversationId = useChatStore((state) => state.conversationId);
  const messages = useChatStore((state) => state.messages);
  const sending = useChatStore((state) => state.sending);
  const error = useChatStore((state) => state.error);
  const escalated = useChatStore((state) => state.escalated);
  const pendingReply = useChatStore((state) => state.pendingReply);
  const loadingConversation = useChatStore((state) => state.loadingConversation);
  const bootstrap = useChatStore((state) => state.bootstrap);
  const startNewConversation = useChatStore((state) => state.startNewConversation);
  const selectConversation = useChatStore((state) => state.selectConversation);
  const sendMessage = useChatStore((state) => state.sendMessage);
  const retryPendingReply = useChatStore((state) => state.retryPendingReply);
  const reset = useChatStore((state) => state.reset);

  const profile = useProfileStore((state) => state.profile);
  const loadProfile = useProfileStore((state) => state.loadProfile);
  const resetProfile = useProfileStore((state) => state.reset);

  const bottomRef = useRef(null);

  const firstName = useMemo(() => {
    const full = user?.customer?.full_name || "";
    return full.split(" ")[0];
  }, [user]);

  const chips = useMemo(() => {
    if (!profile) return [];
    return [
      ...(profile.use_cases || []),
      ...(profile.software || []),
      ...(profile.preferred_brands || []).map((brand) => `Marca: ${brand}`),
      ...(profile.os_label ? [`Sistema: ${profile.os_label}`] : []),
      ...(profile.experience_label ? [`Experiencia: ${profile.experience_label}`] : []),
    ];
  }, [profile]);

  useEffect(() => {
    loadProfile();
    bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const logout = () => {
    clearAuth();
    reset();
    resetProfile();
    navigate("/login");
  };

  return (
    <div className="chat-page">
      <header className="chat-header">
        <div className="brand small">
          <Avatar size="brand" />
          <div>
            <h1>Emmet</h1>
            <p>{escalated ? "Escalada a un asesor" : "Asesor de tecnología"}</p>
          </div>
        </div>
        <div className="header-actions">
          <select
            className="conversation-select"
            value={conversationId ?? ""}
            onChange={(event) => {
              const value = event.target.value;
              if (value) selectConversation(Number(value));
            }}
            aria-label="Conversaciones"
          >
            {conversationId === null && <option value="">Nueva conversación</option>}
            {conversations.map((conversation) => (
              <option key={conversation.id} value={conversation.id}>
                {conversation.title || `Conversación #${conversation.id}`}
              </option>
            ))}
          </select>
          <span className="user-name">{user?.customer?.full_name || user?.email}</span>
          <Link to="/" className="ghost">
            Inicio
          </Link>
          <button className="ghost" onClick={startNewConversation}>
            Nueva
          </button>
          <button className="ghost" onClick={logout}>
            Salir
          </button>
        </div>
      </header>

      {chips.length > 0 && (
        <div className="profile-bar">
          <span className="profile-label">Perfil</span>
          {chips.map((chip) => (
            <span className="profile-chip" key={chip}>
              {chip}
            </span>
          ))}
        </div>
      )}

      <main className="chat-body">
        {loadingConversation ? (
          <p className="muted center">Cargando conversación…</p>
        ) : messages.length === 0 ? (
          <div className="empty-state">
            <Avatar size="large" />
            <h2>Hola{firstName ? `, ${firstName}` : ""}</h2>
            <p>
              Soy Emmet. Puedo ayudarte con productos, pedidos, entregas, garantías
              y soporte.
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))
        )}
        {sending && <TypingIndicator />}

        {pendingReply && !sending && (
          <div className="pending-notice">
            <span>La respuesta anterior no se completó.</span>
            <button className="ghost" onClick={retryPendingReply}>
              Reintentar
            </button>
          </div>
        )}

        {error && <div className="alert inline">{error}</div>}
        <div ref={bottomRef} />
      </main>

      <footer className="chat-footer">
        <ChatInput onSend={sendMessage} disabled={sending || loadingConversation} />
      </footer>
    </div>
  );
}
