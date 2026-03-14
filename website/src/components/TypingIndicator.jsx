export default function TypingIndicator({ status = 'Thinking…' }) {
  return (
    <div className="typing-row">
      <div className="typing-avatar">🍴</div>
      <div className="typing-bubble">
        <div className="typing-dots">
          <span className="dot" />
          <span className="dot" />
          <span className="dot" />
        </div>
        <span className="typing-status">{status}</span>
      </div>
    </div>
  )
}
