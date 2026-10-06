import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


# --------------------------------------------------
# ENVIRONMENT
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# GEMINI CONFIGURATION
# --------------------------------------------------

CHAT_MODEL = "gemini-2.5-flash"


# --------------------------------------------------
# GEMINI CLIENT
# --------------------------------------------------

_client: genai.Client | None = None


def _get_client() -> genai.Client:

    global _client

    if _client is None:

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set in the .env file."
            )

        _client = genai.Client(
            api_key=api_key
        )

    return _client


# --------------------------------------------------
# GENERATE ANSWER
# --------------------------------------------------

def generate_answer(
    question: str,
    context_block: str,
) -> str:

    prompt = (
        "Use the following employee data context to answer "
        "the user's question.\n\n"

        f"Context:\n"
        f"{context_block}\n\n"

        f"Question:\n"
        f"{question}\n\n"

        "Answer concisely using only the provided context."
    )

    response = _get_client().models.generate_content(
        model=CHAT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=(
                "You are an employee data assistant. "
                "Answer questions using only the provided "
                "employee data context. "
                "If the answer cannot be found in the context, "
                "say that the information is not available."
            ),
            temperature=0.2,
            max_output_tokens=1024,
        ),
    )

    return (response.text or "").strip()