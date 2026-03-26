# /app/rag_build.py  (edítalo en tu repo local y reconstruye la imagen)
from pathlib import Path
import json, os, tempfile
import numpy as np

# Dependencias de embedding/índice
from sentence_transformers import SentenceTransformer
import faiss

DATA_DIR = Path(__file__).with_name("data")
PLAN = DATA_DIR / "plan_estudios.json"
CHUNKS = DATA_DIR / "chunks.json"
EXTRA = DATA_DIR / "chunks_extra.json"   # opcional (tus chunks curados)
INDEX = DATA_DIR / "faiss.index"

def load_plan_chunks():
    if not PLAN.exists():
        return []

    with PLAN.open("r", encoding="utf-8") as f:
        plan = json.load(f)

    carreras = plan.get("carreras", [])
    if not carreras:
        return []

    carrera = carreras[0]  # asumimos una carrera
    materias = carrera.get("materias", [])
    areas = carrera.get("areas_enfasis", [])

    # mapa: clave -> [áreas]
    area_por_clave = {}
    for a in areas:
        for clave in a.get("materias_clave", []):
            area_por_clave.setdefault(str(clave), []).append(a.get("nombre", ""))

    chunks = []

    # Materias -> chunks
    for m in materias:
        clave = str(m.get("clave_materia") or m.get("clave") or "").strip()
        if not clave:
            continue

        objetivo = (m.get("objetivo") or "").strip()
        temario = (m.get("contenido_tematico_resumen") or "").strip()
        if not (objetivo or temario):
            # si no hay contenido útil, salta
            continue

        topics = [t.strip() for t in temario.split(",") if t.strip()]

        chunk = {
            "id": f"course:{clave}",
            "type": "course",
            "title": m.get("nombre", f"Curso {clave}"),
            "semester": m.get("semestre"),
            "credits": m.get("creditos"),
            "area": area_por_clave.get(clave, []),
            "prereqs": [p.get("clave") for p in m.get("prerequisitos", []) if isinstance(p, dict) and p.get("clave")],
            "summary": objetivo,
            "syllabus_topics": topics,
            "skills": [],
            "keywords": [],
            "content": (objetivo + "\n" + temario).strip(),
            "source": f"plan_estudios.json#{clave}",
            "intents_supported": ["Search_course","Show_syllabus","Course_requirements","Compare_courses","Recommend_courses_by_degree"]
        }
        chunks.append(chunk)

    # Áreas -> chunks
    for a in areas:
        chunks.append({
            "id": f"area:{a.get('nombre','').lower().strip().replace(' ','_')}",
            "type": "area",
            "title": a.get("nombre"),
            "description": a.get("descripcion"),
            "recommended_paths": [{"name":"Ruta sugerida","path": a.get("materias_clave",[])}],
            "skills": [],
            "keywords": [],
            "qa": [],
            "intents_supported": ["Explore_area_of_emphasis","Recommend_area","Recommend_courses_by_degree"],
            "source": "plan_estudios.json"
        })

    return chunks

def load_extra_chunks():
    if EXTRA.exists():
        with EXTRA.open("r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []

def dedupe(chunks):
    by_id = {}
    for c in chunks:
        cid = c.get("id")
        if cid:
            by_id[cid] = c
    return list(by_id.values())

def write_json_atomic(obj, path: Path):
    fd, tmp = tempfile.mkstemp(prefix=path.stem + ".", suffix=path.suffix, dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)  # reemplazo atómico y seguro
    finally:
        if os.path.exists(tmp):
            try: os.remove(tmp)
            except: pass

def build_faiss_index(chunks):
    texts = []
    for c in chunks:
        if c.get("type") == "course":
            t = " ".join([
                c.get("title",""), c.get("summary",""), c.get("content",""),
                " ".join(c.get("skills",[])), " ".join(c.get("keywords",[]))
            ]).strip()
        else:
            t = " ".join([
                c.get("title",""), c.get("description",""),
                " ".join(c.get("skills",[])), " ".join(c.get("keywords",[]))
            ]).strip()
        if t:
            texts.append(t)

    if not texts:
        print("WARN: no hay textos para indexar; NO sobrescribo faiss.index")
        return False

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    embs = model.encode(texts, normalize_embeddings=True)
    embs = np.asarray(embs, dtype="float32")
    index = faiss.IndexFlatIP(embs.shape[1])
    index.add(embs)
    faiss.write_index(index, str(INDEX))
    return True

def main():
    plan_chunks = load_plan_chunks()
    extra_chunks = load_extra_chunks()
    chunks = dedupe(plan_chunks + extra_chunks)

    if not chunks:
        print("WARN: plan_estudios.json sin datos útiles; NO sobrescribo chunks.json")
        return

    write_json_atomic(chunks, CHUNKS)
    if build_faiss_index(chunks):
        print(f"Index listo: {len(chunks)} chunks.")
    else:
        print("Index NO generado.")

if __name__ == "__main__":
    main()
