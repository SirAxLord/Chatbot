from flask import Flask, request, jsonify
from pathlib import Path
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

app = Flask(__name__)

INDEX_PATH = Path("/app/data/faiss.index")
CHUNKS_PATH = Path("/app/data/chunks.json")

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
index = faiss.read_index(str(INDEX_PATH))
chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))

@app.post("/rag")
def rag():
    data = request.get_json(silent=True) or {}
    q = request.json.get("query","")
    if not q:
        return jsonify({"context": ""})
    q_emb = model.encode([q], convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)
    D, I = index.search(q_emb, k=5)
    ctx = "\n\n".join(chunks[i] for i in I[0] if i < len(chunks))
    return jsonify({"context": ctx})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5056, debug=False)
