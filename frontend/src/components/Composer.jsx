import { useRef, useState } from "react";

export default function Composer({ onSend, disabled }) {
  const [text, setText] = useState("");
  const [recording, setRecording] = useState(false);
  const fileRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  const sendText = () => {
    const t = text.trim();
    if (!t) return;
    onSend({ text: t });
    setText("");
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendText();
    }
  };

  const pickImage = () => fileRef.current?.click();

  const onImageChosen = (e) => {
    const file = e.target.files?.[0];
    if (file) onSend({ text: text.trim(), image: file });
    setText("");
    e.target.value = ""; // allow re-selecting the same file
  };

  const toggleRecording = async () => {
    if (recording) {
      mediaRecorderRef.current?.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => e.data.size > 0 && chunksRef.current.push(e.data);
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        onSend({ text: "", audio: blob });
      };
      mediaRecorderRef.current = mr;
      mr.start();
      setRecording(true);
    } catch (err) {
      alert("Microphone access is required to record a voice note.\n" + err.message);
    }
  };

  return (
    <div className="composer">
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        hidden
        onChange={onImageChosen}
      />

      <button
        className="icon-btn"
        onClick={pickImage}
        disabled={disabled}
        title="Upload a visiting card image"
      >
        📷
      </button>

      <button
        className={`icon-btn ${recording ? "recording" : ""}`}
        onClick={toggleRecording}
        disabled={disabled && !recording}
        title={recording ? "Stop & send voice note" : "Record a voice note"}
      >
        {recording ? "⏹️" : "🎙️"}
      </button>

      <textarea
        className="composer-input"
        rows={1}
        placeholder={
          recording ? "Recording… tap ⏹️ to send" : "Type a message, or upload a card / voice note…"
        }
        value={text}
        disabled={disabled || recording}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
      />

      <button
        className="send-btn"
        onClick={sendText}
        disabled={disabled || recording || !text.trim()}
      >
        Send
      </button>
    </div>
  );
}
