import os

from dotenv import load_dotenv
from openai import OpenAI


# --------------------------------------------------
# ENVIRONMENT
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# OPENROUTER CONFIGURATION
# --------------------------------------------------

CHAT_MODEL = os.getenv(
    "OPENROUTER_CHAT_MODEL",
    "openai/gpt-4o-mini",
)


# --------------------------------------------------
# OPENROUTER CLIENT
# --------------------------------------------------

_client: OpenAI | None = None


def _get_client() -> OpenAI:

    global _client

    if _client is None:

        api_key = os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set in the .env file."
            )

        _client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Cerroalto Employee RAG",
            },
        )

    return _client


# --------------------------------------------------
# GENERATE ANSWER
# --------------------------------------------------

def generate_answer(
    question: str,
    context_block: str,
) -> str:

    response = _get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an employee data assistant. Answer questions "
                    "using only the provided employee data context. If the "
                    "answer cannot be found in the context, say that the "
                    "information is not available."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Context:\n{context_block}\n\n"
                    f"Question:\n{question}"
                ),
            },
        ],
        temperature=0.2,
        max_tokens=1024,
    )

    return (response.choices[0].message.content or "").strip()
