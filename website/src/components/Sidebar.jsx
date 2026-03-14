// Icons as inline SVG components
const IconPlus = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
  </svg>
)

const IconChat = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
)

export default function Sidebar({ conversations, activeId, onSelect, onNewChat, isOpen }) {
  return (
    <aside className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
      <div className="sidebar-header">
        <button className="new-chat-btn" onClick={onNewChat}>
          <IconPlus />
          New chat
        </button>
      </div>

      {conversations.length > 0 && (
        <div className="sidebar-section-label">Recent</div>
      )}

      <div className="sidebar-list">
        {conversations.map(conv => (
          <div
            key={conv.id}
            className={`conv-item ${conv.id === activeId ? 'active' : ''}`}
            onClick={() => onSelect(conv.id)}
          >
            <span className="conv-icon"><IconChat /></span>
            <span className="conv-title">{conv.title}</span>
          </div>
        ))}
      </div>

      <div className="sidebar-footer">
        <div className="brand-row">
          <div className="brand-icon">🍴</div>
          <div>
            <div className="brand-name">Belly Button</div>
            <div className="brand-sub">Restaurant Guide</div>
          </div>
        </div>
      </div>
    </aside>
  )
}
