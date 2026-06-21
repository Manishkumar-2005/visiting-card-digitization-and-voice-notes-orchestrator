export default function Message({ message }) {
  const isUser = message.role === "user";
  const avatar = isUser ? "🧑" : "🤖";

  return (
    <div className={`message ${isUser ? "user" : "assistant"}`}>
      <div className="avatar">{avatar}</div>
      <div className="bubble">
        {message.kind === "image" && message.media_url && (
          <img className="bubble-media" src={message.media_url} alt="visiting card" />
        )}
        {message.kind === "audio" && message.media_url && (
          <audio className="bubble-audio" controls src={message.media_url} />
        )}
        {message.content && (
          <div className="bubble-text">{message.content}</div>
        )}
      </div>
    </div>
  );
}
