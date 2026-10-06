from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from llama_index.core.node_parser import SentenceSplitter
from llama_index.readers.file import PDFReader
from sentence_transformers import SentenceTransformer


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv(
    Path(__file__).parent / ".env"
)


# ============================================================
# LOCAL EMBEDDING MODEL
# ============================================================

# Local Sentence Transformer model
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# all-MiniLM-L6-v2 produces 384-dimensional embeddings
EMBED_DIM = 384


# Load the model once and reuse it
_embedding_model = SentenceTransformer(
    EMBED_MODEL
)


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

    docs = PDFReader().load_data(
        file=path
    )

    texts = [
        document.text
        for document in docs
        if getattr(document, "text", None)
    ]

    chunks = []

    for text in texts:
        chunks.extend(
            splitter.split_text(text)
        )

    return chunks


# ============================================================
# EMPLOYEE CSV LOADING
# ============================================================

def load_employee_csv(path: str) -> list[str]:
    """
    Convert each Employee.csv row
    into a searchable employee record.
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
    Generate local embeddings using
    all-MiniLM-L6-v2.

    task_type is kept in the function signature
    so that main.py does not need to change.

    Sentence Transformers does not require
    RETRIEVAL_DOCUMENT or RETRIEVAL_QUERY
    task types.
    """

    if not texts:
        return []

    vectors = _embedding_model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,
    )

    return vectors.tolist()