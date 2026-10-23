from vector_db import QdrantStorage, COLLECTION

store = QdrantStorage()

info = store.client.get_collection(COLLECTION)

print("Collection:", COLLECTION)
print("Stored points:", info.points_count)