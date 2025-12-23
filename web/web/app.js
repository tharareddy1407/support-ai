const chatEl = document.getElementById("chat");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("sendBtn");

// Step 3: purely local demo state
let sessionId = "local-demo";
document.getElementById("sessionId").textContent = sessionId;

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

function fakeAIReply(userText) {
  // Placeholder only. Real KB-based response comes in Step 4.
  return (
    "Thanks — I’m checking our App Document for a matching issue.\n\n" +
    "For now, please share:\n" +
    "1) Exact error text\n" +
    "2) When it started\n" +
    "3) Screenshot (if available)"
  );
}

function send() {
  const text = inputEl.value.trim();
  if (!text) return;

  addMessage("me", text);
  inputEl.value = "";

  // Step 3: Fake AI response to validate the UI works
  setTimeout(() => {
    addMessage("ai", fakeAIReply(text));
  }, 350);
}

sendBtn.addEventListener("click", send);
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") send();
});

// Initial greeting
addMessage("ai", "Hi! Tell me what issue you’re facing and I’ll guide you step-by-step.");
