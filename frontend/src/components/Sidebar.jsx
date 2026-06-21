export default function Sidebar({ sessions, activeId, onSelect, onNew }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-head">
        <div className="brand">
          <div className="brand-badge">📇</div>
          <div className="brand-name">Card<span>flow</span></div>
        </div>
        <button className="new-btn" onClick={onNew} title="New chat session">
          ＋ New
        </button>
      </div>

      <div className="section-label">Sessions</div>

      <div className="session-list">
        {sessions.length === 0 && (
          <p className="muted small">No sessions yet.</p>
        )}
        {sessions.map((s) => (
          <button
            key={s.session_id}
            className={`session-item ${s.session_id === activeId ? "active" : ""}`}
            onClick={() => onSelect(s.session_id)}
          >
            <div className="session-title">{s.title || "Chat"}</div>
            <div className="session-meta">{s.message_count} msgs</div>
          </button>
        ))}
      </div>

      <div className="sidebar-foot muted small">
        Each session keeps its own agent state, so voice notes link to the right
        card.
      </div>
    </aside>
  );
}
