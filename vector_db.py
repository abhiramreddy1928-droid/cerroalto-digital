from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)


# ============================================================
# QDRANT CONFIGURATION
# ============================================================

# all-MiniLM-L6-v2 produces 384-dimensional embeddings.
EMBED_DIM = 384

# New collection for the local 384-dimensional embeddings.
COLLECTION = "employees_minilm_384"

# Local Qdrant database folder.
QDRANT_PATH = "qdrant_storage"


# ============================================================
# QDRANT CLIENT
# ============================================================

# Create ONE Qdrant client for the application.
_client = QdrantClient(
    path=QDRANT_PATH
)


def _get_client() -> QdrantClient:
    """
    Return the shared Qdrant client.
    """
    return _client


# ============================================================
# QDRANT STORAGE CLASS
# ============================================================

class QdrantStorage:

    def __init__(
        self,
        collection: str = COLLECTION,
        dim: int = EMBED_DIM,
    ):

        self.client = _get_client()
        self.collection = collection
        self.dim = dim

        # ----------------------------------------------------
        # CREATE COLLECTION IF IT DOES NOT EXIST
        # ----------------------------------------------------

        if not self.client.collection_exists(
            self.collection
        ):

            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=self.dim,
                    distance=Distance.COSINE,
                ),
            )


    # ========================================================
    # UPSERT VECTORS
    # ========================================================

    def upsert(
        self,
        ids: list[int],
        vectors: list[list[float]],
        payloads: list[dict],
    ):
        """
        Insert or update employee vectors in Qdrant.
        """

        if not ids:
            return

        if not vectors:
            return

        if not payloads:
            return

        # Make sure all lists have the same length.
        if not (
            len(ids)
            == len(vectors)
            == len(payloads)
        ):
            raise ValueError(
                "IDs, vectors, and payloads must "
                "have the same length."
            )

        # Check embedding dimensions.
        for vector in vectors:

            if len(vector) != self.dim:

                raise ValueError(
                    f"Invalid embedding dimension. "
                    f"Expected {self.dim}, "
                    f"but received {len(vector)}."
                )

        # Create Qdrant points.
        points = [
            PointStruct(
                id=ids[i],
                vector=vectors[i],
                payload=payloads[i],
            )
            for i in range(len(ids))
        ]

        # Store points in Qdrant.
        self.client.upsert(
            collection_name=self.collection,
            points=points,
        )


    # ========================================================
    # SEARCH
    # ========================================================

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
    ) -> dict:
        """
        Search Qdrant for the most similar employee records.
        """

        if not query_vector:
            return {
                "contexts": [],
                "sources": [],
            }

        # Check query embedding dimension.
        if len(query_vector) != self.dim:

            raise ValueError(
                f"Invalid query vector dimension. "
                f"Expected {self.dim}, "
                f"but received {len(query_vector)}."
            )

        # Make sure top_k is valid.
        if top_k <= 0:
            top_k = 5

        # Search Qdrant.
        results = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )

        contexts = []
        sources = []

        # Extract payloads.
        for point in results.points:

            payload = point.payload or {}

            text = str(
                payload.get(
                    "text",
                    "",
                )
            )

            source = str(
                payload.get(
                    "source",
                    "",
                )
            )

            if text:

                contexts.append(text)

                sources.append(source)

        return {
            "contexts": contexts,
            "sources": sources,
        }