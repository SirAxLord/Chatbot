Quickstart (Linux/macOS):

1) Start Ollama and pull a model:
   docker compose up -d ollama
   docker exec -it $(docker ps -qf "name=ollama") bash -lc "ollama pull llama3.1:8b"

2) Train Rasa (optional at first run):
   docker compose run --rm rasa rasa train --domain /app/project/domain.yml --data /app/project

3) Launch stack:
   docker compose up -d --build

4) Open http://localhost and chat. Frontend calls /rasa/webhooks/rest/webhook via Nginx proxy.

Windows (PowerShell):

  docker compose up -d ollama
  $ollama = docker ps --filter "name=ollama" --format "{{.ID}}"
  docker exec -it $ollama bash -lc "ollama pull llama3.1:8b"
  docker compose run --rm rasa rasa train --domain /app/project/domain.yml --data /app/project
  docker compose up -d --build
  # open http://localhost

Frontend note:
 - script.js should POST to /rasa/webhooks/rest/webhook with a stable "sender" (e.g. from localStorage).
