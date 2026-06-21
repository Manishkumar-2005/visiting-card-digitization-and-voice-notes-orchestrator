import { useEffect, useRef, useState, useCallback } from "react";
import { api } from "./api.js";
import Sidebar from "./components/Sidebar.jsx";
import Message from "./components/Message.jsx";
import Composer from "./components/Composer.jsx";
import ConfirmCard from "./components/ConfirmCard.jsx";

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState(null); // {confirmation_prompt, contact}
  const [error, setError] = useState("");
  const scrollRef = useRef(null);

  const refreshSessions = useCallback(async () => {
    const s = await api.listSessions();
    setSessions(s);
    return s;
  }, []);

  const loadMessages = useCallback(async (id) => {
    if (!id) return;
    const m = await api.getMessages(id);
    setMessages(m);
  }, []);

  // Bootstrap: load sessions, create one if none exist.
  useEffect(() => {
    (async () => {
      try {
        let s = await refreshSessions();
        if (s.length === 0) {
          const created = await api.createSession();
          setActiveId(created.session_id);
          await refreshSessions();
        } else {
          setActiveId(s[0].session_id);
        }
      } catch (e) {
        setError(`Could not reach the backend at ${api.base}. ${e.message}`);
      }
    })();
  }, [refreshSessions]);

  useEffect(() => {
    loadMessages(activeId);
    setPending(null);
  }, [activeId, loadMessages]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, busy, pending]);

  const newChat = async () => {
    const created = await api.createSession();
    await refreshSessions();
    setActiveId(created.session_id);
    setMessages([]);
  };

  const handleSend = async ({ text, image, audio }) => {
    if (!activeId || busy) return;
    setError("");
    setBusy(true);
    try {
      const res = await api.chat(activeId, { text, image, audio });
      await loadMessages(activeId);
      await refreshSessions();
      setPending(res.needs_confirmation ? res : null);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const handleConfirm = async (approved) => {
    if (!activeId) return;
    setBusy(true);
    setPending(null);
    try {
      await api.confirm(activeId, approved);
      await loadMessages(activeId);
      await refreshSessions();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="app">
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={newChat}
      />

      <main className="chat">
        <header className="chat-header">
          <div>
            <h1>Visiting Card Orchestrator</h1>
            <p className="subtitle">
              Upload a card to digitize it, then add a voice note — all via a
              single LangGraph agent.
            </p>
          </div>
          <div className="status-pill">
            <span className="status-dot" />
            Agent online
          </div>
        </header>

        <div className="messages" ref={scrollRef}>
          {messages.length === 0 && !busy && (
            <div className="empty-state">
              <div className="hero-orb">📇</div>
              <h2>Digitize a <span>visiting card</span></h2>
              <p className="empty-sub">
                One agent, end to end — extract, dedupe, log to Google Sheets,
                notify on WhatsApp, and attach voice notes to the right contact.
              </p>
              <div className="steps">
                <div className="step">
                  <div className="step-ico">📷</div>
                  <div className="step-title">Upload a card</div>
                  <div className="step-desc">
                    Claude vision extracts the details, checks for duplicates,
                    logs the row, and pings the manager.
                  </div>
                </div>
                <div className="step">
                  <div className="step-ico">🎙️</div>
                  <div className="step-title">Add a voice note</div>
                  <div className="step-desc">
                    Record context — it's attached to that same contact's row
                    automatically.
                  </div>
                </div>
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <Message key={i} message={m} apiBase={api.base} />
          ))}

          {pending && (
            <ConfirmCard
              prompt={pending.confirmation_prompt}
              contact={pending.contact}
              onApprove={() => handleConfirm(true)}
              onCancel={() => handleConfirm(false)}
              disabled={busy}
            />
          )}

          {busy && (
            <div className="message assistant">
              <div className="avatar">🤖</div>
              <div className="bubble typing">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}
        </div>

        {error && <div className="error-bar">{error}</div>}

        <Composer onSend={handleSend} disabled={busy || !activeId || !!pending} />
      </main>
    </div>
  );
}
