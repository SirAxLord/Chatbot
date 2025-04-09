import json
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

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
        
        carrera = "Ingeniería en Sistemas Computacionales"

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

        materia = tracker.get_slot("materia")

        if not materia:
            dispatcher.utter_message(text="Por favor, indícame de qué materia quieres saber los prerequisitos.")
            return []

        try:
            with open('data/plan_estudios.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            dispatcher.utter_message(text="Hubo un error al cargar los datos.")
            return []

        for carrera in data['carreras']:
            for m in carrera['materias']:
                if m['nombre'].lower() == materia.lower():
                    if m['prerequisitos']:
                        dispatcher.utter_message(text=f"Para cursar {m['nombre']} necesitas haber aprobado: {', '.join(m['prerequisitos'])}.")
                    else:
                        dispatcher.utter_message(text=f"{m['nombre']} no tiene prerequisitos.")
                    return []

        dispatcher.utter_message(text=f"No encontré la materia {materia} en el plan de estudios.")
        return []
