import os
import logging
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
    "inclusionai/ling-3.1-flash",
).strip()


# --------------------------------------------------
# OPENROUTER CLIENT
# --------------------------------------------------

_client: OpenAI | None = None


def _get_client() -> OpenAI:

    global _client

    if _client is None:

        raw_key = os.getenv("OPENROUTER_API_KEY", "")
        # Strip leading/trailing whitespace or accidental quotes
        api_key = raw_key.strip().strip("'").strip('"')

        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set in environment variables or .env file."
            )

        _client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=30.0,
            default_headers={
                "HTTP-Referer": "https://cerroalto-digital.onrender.com",
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

    try:
        client = _get_client()
        response = client.chat.completions.create(
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

        msg = response.choices[0].message
        content = msg.content or getattr(msg, "reasoning", "") or ""
        return str(content).strip()

    except Exception as exc:
        logging.exception("OpenRouter generation error: %s", exc)
        err_msg = str(exc)
        if "402" in err_msg or "Insufficient credits" in err_msg:
            return (
                "OpenRouter returned 402 Insufficient Credits. "
                "Please add credits at https://openrouter.ai/settings/credits "
                "or update OPENROUTER_CHAT_MODEL in Render environment variables."
            )
        if "401" in err_msg:
            return (
                "OpenRouter returned 401 Unauthorized. "
                "Please verify OPENROUTER_API_KEY in your environment variables."
            )
        return (
            "I encountered an error communicating with the AI model. "
            "Please check API keys and connection settings."
        )
