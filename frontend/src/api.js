const BASE = "https://visiting-card-backend-bqzz.onrender.com";

async function handle(res) {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} ${text}`);
  }
  return res.json();
}

export const api = {
  base: BASE,

  listSessions: () => fetch(`${BASE}/api/sessions`).then(handle),

  createSession: () =>
    fetch(`${BASE}/api/sessions`, { method: "POST" }).then(handle),

  getMessages: (id) =>
    fetch(`${BASE}/api/sessions/${id}/messages`).then(handle),

  // payload: { text, image: File, audio: Blob }
  chat: (id, { text = "", image = null, audio = null } = {}) => {
    const form = new FormData();
    form.append("text", text);
    if (image) form.append("image", image, image.name || "card.jpg");
    if (audio) form.append("audio", audio, "voice-note.webm");
    return fetch(`${BASE}/api/sessions/${id}/chat`, {
      method: "POST",
      body: form,
    }).then(handle);
  },

  confirm: (id, approved, editedContact = null) =>
    fetch(`${BASE}/api/sessions/${id}/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approved, edited_contact: editedContact }),
    }).then(handle),
};
