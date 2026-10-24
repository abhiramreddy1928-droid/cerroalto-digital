/* =========================================================
   CERROALTO KNOWLEDGE ASSISTANT
   Frontend JavaScript (Production Ready)
   ========================================================= */

// Dynamic API URL:
// If running on a different port locally (e.g. VS Code Live Server on port 5500), point to localhost:8000.
// If served from FastAPI or deployed on Render, use relative '/api/ask'.
const API_URL = (window.location.port && window.location.port !== "8000" && window.location.hostname === "127.0.0.1")
    ? "http://127.0.0.1:8000/api/ask"
    : "/api/ask";

const questionInput = document.getElementById("questionInput");
const chatMessages = document.getElementById("chatMessages");
const welcome = document.getElementById("welcome");
const sendButton = document.getElementById("sendButton");
const chatContainer = document.getElementById("chatContainer");

// Modern SVG User Avatar
const USER_ICON = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="8" r="4"></circle>
        <path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8"></path>
    </svg>
`;

/* =========================================================
   SEND QUESTION
   ========================================================= */
async function sendQuestion() {
    const question = questionInput.value.trim();
    if (!question) return;

    // Hide welcome card on first message
    if (welcome) welcome.style.display = "none";

    // Add user question to stream
    addMessage(question, "user");

    // Reset input
    questionInput.value = "";
    resetTextarea();

    // Disable input while processing
    sendButton.disabled = true;
    const loadingMessage = addLoadingMessage();

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: question,
                top_k: 5
            })
        });

        if (!response.ok) {
            let detail = `Server responded with status ${response.status}`;
            try {
                const err = await response.json();
                if (err.detail) detail = err.detail;
            } catch (e) {
                // Fallback to HTTP status string
            }
            throw new Error(detail);
        }

        const data = await response.json();
        loadingMessage.remove();

        addMessage(
            data.answer || "I received an empty response from the knowledge base.",
            "ai"
        );

    } catch (error) {
        console.error("API Connection Error:", error);
        loadingMessage.remove();

        addMessage(
            `Unable to retrieve an answer right now (${error.message}). If the service just woke up from sleep, please try again in a few seconds.`,
            "ai"
        );
    } finally {
        sendButton.disabled = false;
        questionInput.focus();
    }
}

/* =========================================================
   MESSAGE RENDERING
   ========================================================= */
function addMessage(text, sender) {
    const message = document.createElement("div");

    if (sender === "user") {
        message.className = "message user-message";
        message.innerHTML = `
            <div class="avatar user-avatar" aria-hidden="true">
                ${USER_ICON}
            </div>
            <div class="message-content">
                <div class="message-name">You</div>
                <div class="message-text">${escapeHTML(text)}</div>
            </div>
        `;
    } else {
        message.className = "message ai-message";
        message.innerHTML = `
            <div class="avatar ai-avatar" aria-hidden="true">CA</div>
            <div class="message-content">
                <div class="message-name">CerroAlto Assistant</div>
                <div class="message-text">${formatAIResponse(text)}</div>
            </div>
        `;
    }

    chatMessages.appendChild(message);
    scrollToBottom();
}

function addLoadingMessage() {
    const message = document.createElement("div");
    message.className = "message ai-message";
    message.innerHTML = `
        <div class="avatar ai-avatar" aria-hidden="true">CA</div>
        <div class="message-content">
            <div class="message-name">CerroAlto Assistant</div>
            <div class="typing">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    chatMessages.appendChild(message);
    scrollToBottom();
    return message;
}

function useExample(question) {
    questionInput.value = question;
    questionInput.focus();
    questionInput.style.height = "auto";
    questionInput.style.height = Math.min(questionInput.scrollHeight, 120) + "px";
}

function handleKey(event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendQuestion();
    }
}

questionInput.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = Math.min(this.scrollHeight, 120) + "px";
});

function newChat() {
    chatMessages.innerHTML = "";
    if (welcome) welcome.style.display = "block";
    questionInput.value = "";
    resetTextarea();
    questionInput.focus();

    const sidebar = document.querySelector(".sidebar");
    if (sidebar) sidebar.classList.remove("active");
}

function toggleSidebar() {
    const sidebar = document.querySelector(".sidebar");
    if (sidebar) sidebar.classList.toggle("active");
}

function scrollToBottom() {
    setTimeout(() => {
        chatContainer.scrollTo({
            top: chatContainer.scrollHeight,
            behavior: "smooth"
        });
    }, 50);
}

function resetTextarea() {
    questionInput.style.height = "auto";
}

function escapeHTML(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function formatAIResponse(text) {
    const escaped = escapeHTML(text);
    return escaped.replace(/\n/g, "<br>");
}
