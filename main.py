import logging
from pathlib import Path

import inngest
import inngest.fast_api
from fastapi import FastAPI

from data_loader import (
    EMBED_DIM,
    load_employee_csv,
    embed_texts,
)

from vector_db import QdrantStorage
from gemini_client import generate_answer


# ============================================================
# INNGEST CLIENT
# ============================================================

inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
)


# ============================================================
# 1. EMPLOYEE CSV INGESTION
# ============================================================

@inngest_client.create_function(
    fn_id="RAG: Ingest Employee CSV",
    trigger=inngest.TriggerEvent(
        event="rag/ingest_employee_csv"
    ),
)
async def rag_ingest_employee_csv(ctx: inngest.Context):

    # --------------------------------------------------------
    # CSV PATH
    # --------------------------------------------------------

    csv_path = Path(__file__).parent / "Employee.csv"

    # --------------------------------------------------------
    # LOAD EMPLOYEE CSV
    # --------------------------------------------------------

    texts = await ctx.step.run(
        "load-employee-csv",
        lambda: load_employee_csv(str(csv_path)),
    )

    total_records = len(texts)

    # Process 50 employees at a time
    batch_size = 50

    records_stored = 0

    # --------------------------------------------------------
    # EMBEDDING + QDRANT STORAGE
    # --------------------------------------------------------

    for start in range(0, total_records, batch_size):

        end = min(
            start + batch_size,
            total_records,
        )

        batch_number = (start // batch_size) + 1

        batch_texts = texts[start:end]

        # ----------------------------------------------------
        # Function executed by Inngest step
        # ----------------------------------------------------

        def process_batch(
            batch_texts=batch_texts,
            start=start,
            end=end,
        ):

            # Generate LOCAL embeddings
            vectors = embed_texts(
                batch_texts,
                task_type="RETRIEVAL_DOCUMENT",
            )

            # Create employee IDs
            ids = list(
                range(
                    start + 1,
                    end + 1,
                )
            )

            # Create Qdrant payloads
            payloads = []

            for text, employee_id in zip(
                batch_texts,
                ids,
            ):
                payloads.append(
                    {
                        "text": text,
                        "source": "Employee.csv",
                        "employee_id": employee_id,
                    }
                )

            # Connect to Qdrant
            store = QdrantStorage()

            # Store vectors
            store.upsert(
                ids=ids,
                vectors=vectors,
                payloads=payloads,
            )

            return len(ids)

        # ----------------------------------------------------
        # Run batch as Inngest step
        # ----------------------------------------------------

        stored = await ctx.step.run(
            f"embed-and-store-batch-{batch_number}",
            process_batch,
        )

        records_stored += stored

    # --------------------------------------------------------
    # RETURN INGESTION RESULT
    # --------------------------------------------------------

    return {
        "status": "success",
        "records_loaded": total_records,
        "records_stored": records_stored,
        "collection": "employees_minilm_384",
        "embedding_dimension": EMBED_DIM,
    }


# ============================================================
# 2. QUERY EMPLOYEE DATA
# ============================================================

@inngest_client.create_function(
    fn_id="RAG: Query Employee Data",
    trigger=inngest.TriggerEvent(
        event="rag/query_employee_data"
    ),
)
async def rag_query_employee_data(ctx: inngest.Context):

    # --------------------------------------------------------
    # GET USER QUESTION
    # --------------------------------------------------------

    question = str(
        ctx.event.data.get(
            "question",
            "",
        )
    ).strip()

    if not question:
        return {
            "status": "error",
            "message": "Question is required.",
        }

    # Number of results to retrieve
    top_k = int(
        ctx.event.data.get(
            "top_k",
            5,
        )
    )

    # --------------------------------------------------------
    # SEARCH QDRANT
    # --------------------------------------------------------

    def search_employee_data():

        # Create embedding for user question
        query_vector = embed_texts(
            [question],
            task_type="RETRIEVAL_QUERY",
        )[0]

        # Connect to Qdrant
        store = QdrantStorage()

        # Search similar employee records
        results = store.search(
            query_vector=query_vector,
            top_k=top_k,
        )

        return {
            "contexts": list(
                results.get("contexts", [])
            ),
            "sources": list(
                results.get("sources", [])
            ),
        }

    # --------------------------------------------------------
    # RETRIEVAL STEP
    # --------------------------------------------------------

    found = await ctx.step.run(
        "embed-and-search",
        search_employee_data,
    )

    contexts = found["contexts"]
    sources = found["sources"]

    # --------------------------------------------------------
    # BUILD CONTEXT
    # --------------------------------------------------------

    context_block = "\n\n".join(contexts)

    # --------------------------------------------------------
    # GENERATE ANSWER USING GEMINI
    # --------------------------------------------------------

    answer = await ctx.step.run(
        "generate-answer",
        lambda: generate_answer(
            question,
            context_block,
        ),
    )

    # --------------------------------------------------------
    # RETURN FINAL RESULT
    # --------------------------------------------------------

    return {
        "status": "success",
        "question": question,
        "answer": answer,
        "contexts": contexts,
        "sources": sources,
        "context_block": context_block,
        "num_contexts": len(contexts),
    }


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI()


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def health():

    return {
        "status": "ok",
        "message": "RAG Employee Assistant API is running",
    }


# ============================================================
# INNGEST ENDPOINT
# ============================================================

inngest.fast_api.serve(
    app,
    inngest_client,
    [
        rag_ingest_employee_csv,
        rag_query_employee_data,
    ],
)