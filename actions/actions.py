import os, json
from typing import Any, Dict, List, Text
import requests
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, EventType

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
RAG_URL = os.getenv("RAG_URL", "http://localhost:5056/rag")
MEMORY_PATH = os.getenv("MEMORY_PATH", "/app/memory_store.json")

def _load_memory():
    if not os.path.exists(MEMORY_PATH):
        return {}
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_memory(data):
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def call_ollama(prompt: str, system: str = "") -> str:
    payload = {"model": OLLAMA_MODEL, "prompt": f"{system}\n\n{prompt}" if system else prompt, "stream": False}
    r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data.get("response", "").strip()

class ActionLLMFallback(Action):
    def name(self) -> Text:
        return "action_llm_fallback"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[EventType]:
        user_msg = tracker.latest_message.get("text", "")
        # recent history
        last_lines = []
        # iterate events, collect last ~10 messages
        for ev in tracker.events[-20:]:
            if ev.get("event") == "user" and ev.get("text"):
                last_lines.append(f"USER: {ev.get('text')}")
            elif ev.get("event") == "bot" and ev.get("text"):
                last_lines.append(f"BOT: {ev.get('text')}")
        history = "\n".join(last_lines[-10:])

        user_name = tracker.get_slot("user_name") or "Usuario"
        long_memory = tracker.get_slot("long_memory") or ""

        # RAG
        context = ""
        try:
            r = requests.post(RAG_URL, json={"query": user_msg}, timeout=8)
            if r.ok:
                context = r.json().get("context", "")
        except Exception:
            context = ""

        system_prompt = (
            "Eres un asistente académico para plan de estudios. "
            "Responde de forma breve, clara y con pasos accionables. "
            "Si la pregunta es sobre materias, usa el CONTEXTO. "
            "Si no hay contexto relevante, di que no estás seguro y sugiere cómo precisar."
        )

        full_prompt = f"""
[HISTORIAL]
{history}

[MEMORIA_LARGO_PLAZO]
{long_memory}

[CONTEXTO]
{context}

[INSTRUCCIÓN]
Usuario ({user_name}) dice: "{user_msg}"
Responde en español. Si das listas, usa bullets.
"""

        try:
            answer = call_ollama(full_prompt, system=system_prompt)
        except Exception:
            answer = "Tuve un problema al consultar el modelo. ¿Puedes reformular?"

        dispatcher.utter_message(text=answer)
        return []

class ActionSetUserMemory(Action):
    def name(self) -> Text:
        return "action_set_user_memory"

    def run(self, dispatcher, tracker, domain):
        user_msg = tracker.latest_message.get("text", "")
        store = _load_memory()
        sender_id = tracker.sender_id
        store.setdefault(sender_id, {})
        store[sender_id]["ultimo_interes"] = user_msg
        _save_memory(store)
        pretty = json.dumps(store.get(sender_id), ensure_ascii=False)
        dispatcher.utter_message(text=f"Lo guardé en tu memoria: {pretty}")
        return [SlotSet("long_memory", pretty)]

class ActionDebugMemory(Action):
    def name(self) -> Text:
        return "action_debug_memory"

    def run(self, dispatcher, tracker, domain):
        store = _load_memory()
        data = store.get(tracker.sender_id, {})
        dispatcher.utter_message(text=f"Memoria actual: {json.dumps(data, ensure_ascii=False)}")
        return []
