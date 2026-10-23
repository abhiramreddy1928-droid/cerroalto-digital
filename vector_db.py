from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from data_loader import COLLECTION, EMBED_DIM


QDRANT_PATH = Path(__file__).parent / "qdrant_storage"


_client = QdrantClient(path=str(QDRANT_PATH))


def _get_client() -> QdrantClient:
    """
    Return the shared Qdrant client.
    """

    return _client


class QdrantStorage:

    def __init__(
        self,
        collection: str = COLLECTION,
        dim: int = EMBED_DIM,
    ):
        self.client = _get_client()
        self.collection = collection
        self.dim = dim

        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=self.dim,
                    distance=Distance.COSINE,
                ),
            )
        else:
            collection_info = self.client.get_collection(
                self.collection
            )
            vector_config = collection_info.config.params.vectors
            existing_dim = getattr(vector_config, "size", None)
            existing_distance = getattr(
                vector_config,
                "distance",
                None,
            )

            if existing_dim != self.dim:
                raise RuntimeError(
                    f"Qdrant collection '{self.collection}' uses "
                    f"{existing_dim}-dimensional vectors, but this "
                    f"application is configured for {self.dim}. "
                    "Use a new collection or recreate the existing "
                    "one before ingesting data."
                )

            if existing_distance != Distance.COSINE:
                raise RuntimeError(
                    f"Qdrant collection '{self.collection}' does not "
                    "use cosine distance."
                )

    def upsert(
        self,
        ids: list[int],
        vectors: list[list[float]],
        payloads: list[dict],
    ) -> None:
        """
        Insert or update employee vectors in Qdrant.
        """

        if not ids:
            return

        if not (
            len(ids)
            == len(vectors)
            == len(payloads)
        ):
            raise ValueError(
                "IDs, vectors, and payloads must have the same length."
            )

        for vector in vectors:
            if len(vector) != self.dim:
                raise ValueError(
                    f"Invalid embedding dimension. Expected "
                    f"{self.dim}, but received {len(vector)}."
                )

        points = [
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
            for point_id, vector, payload in zip(
                ids,
                vectors,
                payloads,
            )
        ]

        self.client.upsert(
            collection_name=self.collection,
            points=points,
        )

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

        if len(query_vector) != self.dim:
            raise ValueError(
                f"Invalid query vector dimension. Expected "
                f"{self.dim}, but received {len(query_vector)}."
            )

        if top_k <= 0:
            top_k = 5

        results = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )

        contexts = []
        sources = []

        for point in results.points:
            payload = point.payload or {}
            text = str(payload.get("text", ""))
            source = str(payload.get("source", ""))

            if text:
                contexts.append(text)
                sources.append(source)

        return {
            "contexts": contexts,
            "sources": sources,
        }