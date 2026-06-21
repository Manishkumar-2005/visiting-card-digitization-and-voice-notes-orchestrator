// Human-in-the-loop confirmation card (bonus). Shown when the agent interrupts
// and asks the user to confirm extracted details before writing to Sheets /
// sending the WhatsApp alert.
export default function ConfirmCard({ prompt, contact, onApprove, onCancel, disabled }) {
  const c = contact || {};
  const rows = [
    ["Name", c.name],
    ["Phone", c.phone],
    ["Email", c.email],
    ["Company", c.company],
    ["Title", c.title],
    ["Website", c.website],
    ["LinkedIn", c.linkedin],
  ].filter(([, v]) => v);

  return (
    <div className="message assistant">
      <div className="avatar">🤖</div>
      <div className="bubble confirm-card">
        <div className="confirm-title">{prompt || "Confirm these details?"}</div>
        <table className="confirm-table">
          <tbody>
            {rows.map(([k, v]) => (
              <tr key={k}>
                <td className="k">{k}</td>
                <td className="v">{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="confirm-actions">
          <button className="btn-approve" onClick={onApprove} disabled={disabled}>
            ✅ Confirm & save
          </button>
          <button className="btn-cancel" onClick={onCancel} disabled={disabled}>
            ✋ Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
