from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from llama_index.core.node_parser import SentenceSplitter
from llama_index.readers.file import PDFReader


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv(Path(__file__).parent / ".env")


# ============================================================
# LOCAL EMBEDDING CONFIGURATION
# ============================================================

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIM = 384
COLLECTION = "employees_minilm_384"

_model: Any | None = None


def _get_model() -> Any:
    """
    Load the local embedding model once and reuse it.
    The first run downloads the model (about 90 MB) and caches it.
    """

    global _model

    if _model is None:
        try:
            # Keep this import lazy. It prevents a Windows policy block on
            # SciPy from stopping direct CSV questions and the whole API.
            from sentence_transformers import SentenceTransformer
        except (ImportError, OSError) as exc:
            raise RuntimeError(
                "The local embedding model could not start because Windows "
                "blocked a required SciPy component. Direct CSV questions "
                "still work, but RAG retrieval needs an approved Python/"
                "SciPy installation."
            ) from exc

        _model = SentenceTransformer(EMBED_MODEL)

    return _model


# ============================================================
# PDF CHUNKING
# ============================================================

splitter = SentenceSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)


def load_and_chunk_pdf(path: str) -> list[str]:
    """
    Load a PDF and split its text into chunks.
    """

    docs = PDFReader().load_data(file=path)

    texts = [
        document.text
        for document in docs
        if getattr(document, "text", None)
    ]

    chunks = []

    for text in texts:
        chunks.extend(splitter.split_text(text))

    return chunks


# ============================================================
# EMPLOYEE CSV LOADING
# ============================================================

def load_employee_csv(path: str) -> list[str]:
    """
    Convert each Employee.csv row into a searchable record.
    """

    df = pd.read_csv(path)

    texts = []

    for index, row in df.iterrows():
        text = (
            f"Employee record {index + 1}. "
            f"Education: {row['Education']}. "
            f"Joining Year: {row['JoiningYear']}. "
            f"City: {row['City']}. "
            f"Payment Tier: {row['PaymentTier']}. "
            f"Age: {row['Age']}. "
            f"Gender: {row['Gender']}. "
            f"Ever Benched: {row['EverBenched']}. "
            f"Experience in Current Domain: "
            f"{row['ExperienceInCurrentDomain']} years. "
            f"Leave or Not: {row['LeaveOrNot']}."
        )

        texts.append(text)

    return texts


# ============================================================
# LOCAL EMBEDDINGS
# ============================================================

def embed_texts(
    texts: list[str],
    task_type: str = "RETRIEVAL_DOCUMENT",
) -> list[list[float]]:
    """
    Generate 384-dimensional embeddings locally with
    all-MiniLM-L6-v2. No API key or internet is needed after the
    model has been downloaded once.

    task_type is accepted so main.py does not need to change;
    MiniLM uses the same encoding for documents and queries.
    """

    if not texts:
        return []

    vectors = _get_model().encode(
        texts,
        batch_size=32,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )

    result = [vector.tolist() for vector in vectors]

    if len(result) != len(texts):
        raise RuntimeError(
            "Embedding model returned a different number of "
            "embeddings than the number of supplied texts."
        )

    for vector in result:
        if len(vector) != EMBED_DIM:
            raise RuntimeError(
                f"Embedding has dimension {len(vector)}; "
                f"expected {EMBED_DIM}."
            )

    return result
