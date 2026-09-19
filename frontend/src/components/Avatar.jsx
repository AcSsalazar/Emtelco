import chatbotIcon from "../public/chatbot-ico.png";

export default function Avatar({ size = "md" }) {
  return (
    <div className={`avatar avatar-${size}`}>
      <img src={chatbotIcon} alt="Emmet" />
    </div>
  );
}
