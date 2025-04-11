import json
import unicodedata  # Para normalizar textos (quitar acentos, etc.)
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

def normalize_text(text: Text) -> Text:
    """
    Elimina acentos y convierte el texto a minúsculas.
    """
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", errors="ignore").decode("utf-8").lower()

class ActionProvidePlanEstudios(Action):
    def name(self) -> Text:
        return "action_provide_plan_estudios"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        try:
            with open('data/plan_estudios.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            dispatcher.utter_message(text="Hubo un error al cargar el plan de estudios.")
            return []
        
        # Definir la carrera a buscar
        carrera = "Ingeniería en Sistemas Computacionales"

        # Se compara de forma exacta (sin normalización en esta versión)
        plan = next((c for c in data['carreras'] if c['nombre'] == carrera), None)
        
        if plan:
            materias_por_semestre = {}
            for materia in plan['materias']:
                semestre = materia['semestre']
                materias_por_semestre.setdefault(semestre, []).append(materia['nombre'])
            
            mensaje = f"Plan de estudios de {carrera} ({plan['duracion']}):\n\n"
            for semestre in sorted(materias_por_semestre.keys()):
                mensaje += f"Semestre {semestre}: {', '.join(materias_por_semestre[semestre])}\n"
            
            dispatcher.utter_message(text=mensaje)
        else:
            dispatcher.utter_message(text="Lo siento, no encontré información sobre esa carrera.")
        
        return []

class ActionProvidePrerequisitos(Action):
    def name(self) -> Text:
        return "action_provide_prerequisitos"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # 1. Obtener el slot "materia" y el último mensaje del usuario
        materia_slot = tracker.get_slot("materia")
        user_message = tracker.latest_message.get('text', '')
        
        # Debug: mostramos lo que se obtiene
        print(f"DEBUG: materia_slot: '{materia_slot}'")
        print(f"DEBUG: user_message: '{user_message}'")
        
        # Usamos el valor del slot si existe, sino usamos el mensaje completo
        if materia_slot:
            materia_usuario = normalize_text(materia_slot)
        else:
            materia_usuario = normalize_text(user_message)
        
        print(f"DEBUG: materia_usuario (normalizada): '{materia_usuario}'")
        
        if not materia_usuario.strip():
            dispatcher.utter_message(text="Por favor, indícame de qué materia quieres saber los prerequisitos.")
            return []

        # 2. Abrir y cargar el archivo JSON con el plan de estudios
        try:
            with open('data/plan_estudios.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            dispatcher.utter_message(text="Hubo un error al cargar los datos del plan de estudios.")
            print(f"ERROR: {e}")
            return []

        # 3. Buscar la materia en cada carrera
        # Recorremos las carreras y materias, normalizando cada nombre para la comparación
        materia_encontrada = None
        for carrera in data['carreras']:
            for m in carrera['materias']:
                nombre_materia_normalizado = normalize_text(m['nombre'])
                print(f"DEBUG: comparando '{materia_usuario}' con '{nombre_materia_normalizado}'")
                if nombre_materia_normalizado == materia_usuario:
                    materia_encontrada = m
                    break
            if materia_encontrada:
                break

        if not materia_encontrada:
            dispatcher.utter_message(text=f"No encontré la materia '{user_message}' en el plan de estudios.")
            return []

        # 4. Responder mostrando los prerequisitos (si existen) o indicar que no tiene
        prerequisitos = materia_encontrada.get('prerequisitos', [])
        if prerequisitos:
            prereq_list = ', '.join(prerequisitos)
            dispatcher.utter_message(text=f"Para cursar {materia_encontrada['nombre']} necesitas haber aprobado: {prereq_list}.")
        else:
            dispatcher.utter_message(text=f"{materia_encontrada['nombre']} no tiene prerequisitos.")
        
        return []
