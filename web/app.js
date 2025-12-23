const chatEl = document.getElementById("chat");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("sendBtn");
const sessionIdEl = document.getElementById("sessionId");

let sessionId = localStorage.getItem("support_session_id") || null;
sessionIdEl.textContent = sessionId || "not-started";

function addMessage(role, text) {
  const row = document.createElement("div");
  row.className = `msg ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  row.appendChild(bubble);
  chatEl.appendChild(row);
  chatEl.scrollTop = chatEl.scrollHeight;
}

async function sendToBackend(message) {
  const res = await fetch("http://127.0.0.1:8000/support/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      customer_id: "customer-001",
      message,
      context: { channel: "website" }
    })
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Backend error ${res.status}: ${txt}`);
  }
  return await res.json();
}

async function send() {
  const text = inputEl.value.trim();
  if (!text) return;

  addMessage("me", text);
  inputEl.value = "";

  try {
    const data = await sendToBackend(text);

    sessionId = data.session_id;
    localStorage.setItem("support_session_id", sessionId);
    sessionIdEl.textContent = sessionId;

    addMessage("ai", data.reply);
  } catch (err) {
    addMessage("ai", `❌ Could not reach support service.\n${err.message}`);
  }
}

sendBtn.addEventListener("click", send);
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") send();
});

addMessage("ai", "Hi! Tell me what issue you’re facing and I’ll guide you step-by-step.");
