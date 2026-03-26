FROM rasa/rasa-sdk:3.13.0
USER root

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY actions.py rag_build.py rag_server.py /app/
COPY data /app/data

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
 && pip install --no-cache-dir \
    "numpy<2.0" \
    "sentence-transformers==3.0.1" \
    "faiss-cpu==1.8.0" \
    "flask==3.0.3" \
    "gunicorn==22.0.0" \
    "requests==2.32.3" \
    "supervisor==4.2.5"

# Construye el índice RAG
RUN python /app/rag_build.py

# Supervisord corre SDK + RAG
RUN printf "[supervisord]\nnodaemon=true\n\n[program:sdk]\ncommand=python -m rasa_sdk --actions actions\n\n[program:rag]\ncommand=gunicorn -w 1 -b 0.0.0.0:5056 rag_server:app\n" > /etc/supervisor.conf

# (clave) anula el ENTRYPOINT heredado que busca ./entrypoint.sh
ENTRYPOINT []
CMD ["supervisord", "-c", "/etc/supervisor.conf"]
