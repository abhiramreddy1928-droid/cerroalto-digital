<<<<<<< HEAD
/* =========================================================
   CERROALTO KNOWLEDGE ASSISTANT
   Frontend JavaScript
   ========================================================= */


// Backend endpoint (FastAPI: POST /api/ask)
const API_URL = "http://127.0.0.1:8000/api/ask";


const questionInput = document.getElementById("questionInput");

const chatMessages = document.getElementById("chatMessages");

const welcome = document.getElementById("welcome");

const sendButton = document.getElementById("sendButton");

const chatContainer = document.getElementById("chatContainer");


// User avatar icon (inherits the avatar's text color)
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

    if (!question) {
        return;
    }


    // Hide welcome screen

    welcome.style.display = "none";


    // Add user's question

    addMessage(question, "user");


    // Clear input

    questionInput.value = "";

    resetTextarea();


    // Disable send button

    sendButton.disabled = true;


    // Show loading animation

    const loadingMessage = addLoadingMessage();


    try {

        /*
         * Request:  { "question": "...", "top_k": 5 }
         * Response: { "answer": "...", "contexts": [...], "sources": [...] }
         */

        const response = await fetch(
    "http://127.0.0.1:8000/api/ask",
    {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            question: question
        })
    }
);


        if (!response.ok) {

            let detail = `Backend returned ${response.status}`;

            try {
                const err = await response.json();
                if (err.detail) {
                    detail = err.detail;
                }
            } catch (e) {
                // response was not JSON; keep the default message
            }

            throw new Error(detail);

        }


        const data = await response.json();


        // Remove loading message

        loadingMessage.remove();


        // Display AI answer

        addMessage(
            data.answer || "I received an empty response.",
            "ai"
        );


    } catch (error) {

        console.error(
            "Backend connection error:",
            error
        );


        loadingMessage.remove();


        addMessage(
            "I’m unable to get an answer right now. Please make sure the backend server and Ollama are running. (" +
            error.message +
            ")",
            "ai"
        );

    } finally {

        sendButton.disabled = false;

        questionInput.focus();

    }

}


/* =========================================================
   ADD MESSAGE
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

                <div class="message-name">
                    User
                </div>

                <div class="message-text">
                    ${escapeHTML(text)}
                </div>

            </div>

        `;

    } else {

        message.className = "message ai-message";

        message.innerHTML = `

            <div class="avatar ai-avatar" aria-hidden="true">
                CA
            </div>

            <div class="message-content">

                <div class="message-name">
                    CerroAlto Assistant
                </div>

                <div class="message-text">
                    ${escapeHTML(text)}
                </div>

            </div>

        `;

    }


    chatMessages.appendChild(message);


    scrollToBottom();

}


/* =========================================================
   LOADING MESSAGE
   ========================================================= */

function addLoadingMessage() {

    const message = document.createElement("div");

    message.className = "message ai-message";


    message.innerHTML = `

        <div class="avatar ai-avatar" aria-hidden="true">
            CA
        </div>

        <div class="message-content">

            <div class="message-name">
                CerroAlto Assistant
            </div>

            <div class="typing">

                <span></span>
                <span></span>
                <span></span>

            </div>

        </div>

    `;


    chatMessages.appendChild(message);


    scrollToBottom();


    return message;

}


/* =========================================================
   USE EXAMPLE QUESTION
   ========================================================= */

function useExample(question) {

    questionInput.value = question;

    questionInput.focus();


    // Automatically resize textarea

    questionInput.style.height = "auto";

    questionInput.style.height =
        Math.min(
            questionInput.scrollHeight,
            120
        ) + "px";

}


/* =========================================================
   ENTER KEY
   ========================================================= */

function handleKey(event) {

    if (
        event.key === "Enter" &&
        !event.shiftKey
    ) {

        event.preventDefault();

        sendQuestion();

    }

}


/* =========================================================
   TEXTAREA AUTO RESIZE
   ========================================================= */

questionInput.addEventListener(
    "input",
    function () {

        this.style.height = "auto";

        this.style.height =
            Math.min(
                this.scrollHeight,
                120
            ) + "px";

    }
);


/* =========================================================
   NEW CHAT
   ========================================================= */

function newChat() {

    chatMessages.innerHTML = "";

    welcome.style.display = "block";

    questionInput.value = "";

    resetTextarea();

    questionInput.focus();


    // Close sidebar on mobile

    const sidebar =
        document.querySelector(".sidebar");

    sidebar.classList.remove("active");

}


/* =========================================================
   MOBILE SIDEBAR
   ========================================================= */

function toggleSidebar() {

    const sidebar =
        document.querySelector(".sidebar");

    sidebar.classList.toggle("active");

}


/* =========================================================
   SCROLL CHAT
   ========================================================= */

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

    const div =
        document.createElement("div");

    div.textContent = text;

    return div.innerHTML;

=======
/* =========================================================
   CERROALTO KNOWLEDGE ASSISTANT
   Frontend JavaScript
   ========================================================= */


// Backend endpoint (FastAPI: POST /api/ask)
const API_URL = "http://127.0.0.1:8000/api/ask";


const questionInput = document.getElementById("questionInput");

const chatMessages = document.getElementById("chatMessages");

const welcome = document.getElementById("welcome");

const sendButton = document.getElementById("sendButton");

const chatContainer = document.getElementById("chatContainer");


/* =========================================================
   SEND QUESTION
   ========================================================= */

async function sendQuestion() {

    const question = questionInput.value.trim();

    if (!question) {
        return;
    }


    // Hide welcome screen

    welcome.style.display = "none";


    // Add user's question

    addMessage(question, "user");


    // Clear input

    questionInput.value = "";

    resetTextarea();


    // Disable send button

    sendButton.disabled = true;


    // Show loading animation

    const loadingMessage = addLoadingMessage();


    try {

        /*
         * Request:  { "question": "...", "top_k": 5 }
         * Response: { "answer": "...", "contexts": [...], "sources": [...] }
         */

        const response = await fetch(
            API_URL,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    question: question,
                    top_k: 5
                })
            }
        );


        if (!response.ok) {

            let detail = `Backend returned ${response.status}`;

            try {
                const err = await response.json();
                if (err.detail) {
                    detail = err.detail;
                }
            } catch (e) {
                // response was not JSON; keep the default message
            }

            throw new Error(detail);

        }


        const data = await response.json();


        // Remove loading message

        loadingMessage.remove();


        // Display AI answer

        addMessage(
            data.answer || "I received an empty response.",
            "ai"
        );


    } catch (error) {

        console.error(
            "Backend connection error:",
            error
        );


        loadingMessage.remove();


        addMessage(
            "I’m unable to get an answer right now. Please make sure the backend server and Ollama are running. (" +
            error.message +
            ")",
            "ai"
        );

    } finally {

        sendButton.disabled = false;

        questionInput.focus();

    }

}


/* =========================================================
   ADD MESSAGE
   ========================================================= */

function addMessage(text, sender) {

    const message = document.createElement("div");

    message.className = "message";


    if (sender === "user") {

        message.innerHTML = `

            <div class="avatar user-avatar">
                YOU
            </div>

            <div class="message-content">

                <div class="message-name">
                    You
                </div>

                <div class="message-text">
                    ${escapeHTML(text)}
                </div>

            </div>

        `;

    } else {

        message.innerHTML = `

            <div class="avatar ai-avatar">
                CA
            </div>

            <div class="message-content">

                <div class="message-name">
                    CerroAlto Assistant
                </div>

                <div class="message-text">
                    ${escapeHTML(text)}
                </div>

            </div>

        `;

    }


    chatMessages.appendChild(message);


    scrollToBottom();

}


/* =========================================================
   LOADING MESSAGE
   ========================================================= */

function addLoadingMessage() {

    const message = document.createElement("div");

    message.className = "message";


    message.innerHTML = `

        <div class="avatar ai-avatar">
            CA
        </div>

        <div class="message-content">

            <div class="message-name">
                CerroAlto Assistant
            </div>

            <div class="typing">

                <span></span>
                <span></span>
                <span></span>

            </div>

        </div>

    `;


    chatMessages.appendChild(message);


    scrollToBottom();


    return message;

}


/* =========================================================
   USE EXAMPLE QUESTION
   ========================================================= */

function useExample(question) {

    questionInput.value = question;

    questionInput.focus();


    // Automatically resize textarea

    questionInput.style.height = "auto";

    questionInput.style.height =
        Math.min(
            questionInput.scrollHeight,
            120
        ) + "px";

}


/* =========================================================
   ENTER KEY
   ========================================================= */

function handleKey(event) {

    if (
        event.key === "Enter" &&
        !event.shiftKey
    ) {

        event.preventDefault();

        sendQuestion();

    }

}


/* =========================================================
   TEXTAREA AUTO RESIZE
   ========================================================= */

questionInput.addEventListener(
    "input",
    function () {

        this.style.height = "auto";

        this.style.height =
            Math.min(
                this.scrollHeight,
                120
            ) + "px";

    }
);


/* =========================================================
   NEW CHAT
   ========================================================= */

function newChat() {

    chatMessages.innerHTML = "";

    welcome.style.display = "block";

    questionInput.value = "";

    resetTextarea();

    questionInput.focus();


    // Close sidebar on mobile

    const sidebar =
        document.querySelector(".sidebar");

    sidebar.classList.remove("active");

}


/* =========================================================
   MOBILE SIDEBAR
   ========================================================= */

function toggleSidebar() {

    const sidebar =
        document.querySelector(".sidebar");

    sidebar.classList.toggle("active");

}


/* =========================================================
   SCROLL CHAT
   ========================================================= */

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

    const div =
        document.createElement("div");

    div.textContent = text;

    return div.innerHTML;

>>>>>>> 0a3fd9b894c747b7917e97fab7f070c9e818edd4
}