import os

import requests
from dotenv import load_dotenv


# --------------------------------------------------
# ENVIRONMENT
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# OLLAMA CONFIGURATION
# --------------------------------------------------

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
CHAT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

SYSTEM_PROMPT = (
    "You are an employee data assistant. "
    "Answer questions using only the provided "
    "employee data context. "
    "If the answer cannot be found in the context, "
    "say that the information is not available."
)


# --------------------------------------------------
# GENERATE ANSWER
# --------------------------------------------------

def generate_answer(
    question: str,
    context_block: str,
) -> str:
    user_prompt = (
        "Use the following employee data context to answer "
        "the user's question.\n\n"
        f"Context:\n{context_block}\n\n"
        f"Question:\n{question}\n\n"
        "Answer concisely using only the provided context."
    )

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": CHAT_MODEL,
                "stream": False,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "options": {
                    "temperature": 0.2,
                    "num_predict": 1024,
                },
            },
            timeout=300,
        )
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Cannot reach Ollama at {OLLAMA_URL}. "
            "Make sure the Ollama app is running."
        )

    if response.status_code == 404:
        raise RuntimeError(
            f"Ollama model '{CHAT_MODEL}' not found. "
            f"Run: ollama pull {CHAT_MODEL}"
        )

    response.raise_for_status()

    data = response.json()

    return (data.get("message", {}).get("content") or "").strip()