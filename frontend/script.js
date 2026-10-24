/* =========================================================
   CERROALTO KNOWLEDGE ASSISTANT
   Frontend JavaScript (Production Ready with Stop Thinking)
   ========================================================= */

// Dynamic API URL:
// 1. If running with a dev server on a different port (e.g. Live Server on 5500), target port 8000 on the same host.
// 2. If served directly by FastAPI or deployed on Render (e.g. port 8000 or 10000), use relative '/api/ask'.
const isDevFrontend = window.location.port && window.location.port !== "8000" && window.location.port !== "10000";
const API_URL = isDevFrontend
    ? `http://${window.location.hostname || "127.0.0.1"}:8000/api/ask`
    : "/api/ask";

const questionInput = document.getElementById("questionInput");
const chatMessages = document.getElementById("chatMessages");
const welcome = document.getElementById("welcome");
const sendButton = document.getElementById("sendButton");
const chatContainer = document.getElementById("chatContainer");

// Generation and cancellation state
let isGenerating = false;
let currentAbortController = null;
let currentLoadingMessage = null;

// Modern SVG User Avatar
const USER_ICON = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="8" r="4"></circle>
        <path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8"></path>
    </svg>
`;

/* =========================================================
   SEND OR STOP ACTION DISPATCHER
   ========================================================= */
function handleSendOrStop() {
    if (isGenerating) {
        stopThinking();
    } else {
        sendQuestion();
    }
}

/* =========================================================
   STOP THINKING / GENERATION
   ========================================================= */
function stopThinking() {
    if (!isGenerating && !currentAbortController) return;

    if (currentAbortController) {
        try {
            currentAbortController.abort();
        } catch (e) {
            console.error("Error aborting request:", e);
        }
    }

    if (currentLoadingMessage) {
        updateStoppedMessage(currentLoadingMessage);
        currentLoadingMessage = null;
    }

    isGenerating = false;
    currentAbortController = null;
    setGeneratingUI(false);
    questionInput.focus();
}

function updateStoppedMessage(loadingElem) {
    if (!loadingElem || !loadingElem.parentNode) return;
    loadingElem.classList.remove("loading-message");
    const content = loadingElem.querySelector(".message-content");
    if (content) {
        content.innerHTML = `
            <div class="message-name">CerroAlto Assistant</div>
            <div class="message-stopped">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line>
                </svg>
                <span>Thinking stopped by user</span>
            </div>
        `;
    }
    scrollToBottom();
}

/* =========================================================
   UI STATE TOGGLE (THINKING / IDLE)
   ========================================================= */
function setGeneratingUI(generating) {
    const stopContainer = document.getElementById("stopContainer");
    const sendIcon = sendButton ? sendButton.querySelector(".send-icon") : null;
    const stopIcon = sendButton ? sendButton.querySelector(".stop-icon") : null;

    if (generating) {
        if (stopContainer) stopContainer.style.display = "flex";
        if (sendButton) {
            sendButton.classList.add("is-generating");
            sendButton.disabled = false;
            sendButton.setAttribute("aria-label", "Stop thinking");
            sendButton.title = "Stop thinking (Esc)";
        }
        if (sendIcon) sendIcon.style.display = "none";
        if (stopIcon) stopIcon.style.display = "block";
        questionInput.placeholder = "Thinking... Click Stop or press Esc to cancel";
    } else {
        if (stopContainer) stopContainer.style.display = "none";
        if (sendButton) {
            sendButton.classList.remove("is-generating");
            sendButton.disabled = false;
            sendButton.setAttribute("aria-label", "Send question");
            sendButton.title = "Send question";
        }
        if (sendIcon) sendIcon.style.display = "block";
        if (stopIcon) stopIcon.style.display = "none";
        questionInput.placeholder = "Ask something about the company...";
    }
}

/* =========================================================
   SEND QUESTION
   ========================================================= */
async function sendQuestion() {
    if (isGenerating) return;

    const question = questionInput.value.trim();
    if (!question) return;

    // Hide welcome card on first message
    if (welcome) welcome.style.display = "none";

    // Add user question to stream
    addMessage(question, "user");

    // Reset input
    questionInput.value = "";
    resetTextarea();

    // Prepare generation state and UI
    isGenerating = true;
    setGeneratingUI(true);
    currentLoadingMessage = addLoadingMessage();
    currentAbortController = new AbortController();

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: question,
                top_k: 5
            }),
            signal: currentAbortController.signal
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

        // If stopped in-flight, do not overwrite stopped message
        if (!isGenerating) return;

        if (currentLoadingMessage) {
            currentLoadingMessage.remove();
            currentLoadingMessage = null;
        }

        addMessage(
            data.answer || "I received an empty response from the knowledge base.",
            "ai"
        );

    } catch (error) {
        if (error.name === "AbortError") {
            // User requested to stop thinking
            console.log("Chat response stopped by user.");
            if (currentLoadingMessage) {
                updateStoppedMessage(currentLoadingMessage);
                currentLoadingMessage = null;
            }
        } else {
            console.error("API Connection Error:", error);
            if (currentLoadingMessage) {
                currentLoadingMessage.remove();
                currentLoadingMessage = null;
            }

            addMessage(
                `Unable to retrieve an answer right now (${error.message}). If the service just woke up from sleep, please try again in a few seconds.`,
                "ai"
            );
        }
    } finally {
        isGenerating = false;
        currentAbortController = null;
        setGeneratingUI(false);
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
    message.className = "message ai-message loading-message";
    message.innerHTML = `
        <div class="avatar ai-avatar" aria-hidden="true">CA</div>
        <div class="message-content">
            <div class="message-name">CerroAlto Assistant</div>
            <div class="thinking-row">
                <div class="typing" aria-label="Thinking">
                    <span></span><span></span><span></span>
                </div>
                <span class="thinking-text">Thinking...</span>
                <button
                    type="button"
                    class="inline-stop-btn"
                    onclick="stopThinking()"
                    aria-label="Stop thinking"
                    title="Stop thinking"
                >
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                        <rect x="4" y="4" width="16" height="16" rx="2"></rect>
                    </svg>
                    <span>Stop</span>
                </button>
            </div>
        </div>
    `;
    chatMessages.appendChild(message);
    scrollToBottom();
    return message;
}

function useExample(question) {
    if (isGenerating) {
        stopThinking();
    }
    questionInput.value = question;
    questionInput.focus();
    questionInput.style.height = "auto";
    questionInput.style.height = Math.min(questionInput.scrollHeight, 120) + "px";
}

function handleKey(event) {
    if (event.key === "Escape" && isGenerating) {
        event.preventDefault();
        stopThinking();
        return;
    }
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        if (isGenerating) return;
        sendQuestion();
    }
}

// Global escape key handler to cancel thinking even if focus is shifted
window.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && isGenerating) {
        stopThinking();
    }
});

questionInput.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = Math.min(this.scrollHeight, 120) + "px";
});

function newChat() {
    if (isGenerating) {
        stopThinking();
    }
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
    let formatted = escapeHTML(text);
    // Replace **bold** with <strong>bold</strong>
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Replace *italic* with <em>italic</em>
    formatted = formatted.replace(/\*(.*?)\*/g, "<em>$1</em>");
    // Replace newlines with <br>
    return formatted.replace(/\n/g, "<br>");
}
