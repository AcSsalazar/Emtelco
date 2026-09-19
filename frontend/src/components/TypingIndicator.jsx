import Avatar from "./Avatar";

export default function TypingIndicator() {
  return (
    <div className="message-row is-assistant">
      <Avatar />
      <div className="bubble assistant typing">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
        <span className="typing-label">Emmet está consultando información…</span>
      </div>
    </div>
  );
}
