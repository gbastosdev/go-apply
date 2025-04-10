from sentence_transformers import SentenceTransformer, util
from routes import router
from threading import Thread

# documents = []

# model = SentenceTransformer("all-MiniLM-L6-v2")
# embedded_docs = {
#     doc["id"]: model.encode(doc['text'],convert_to_tensor=True) for doc in documents
# }
