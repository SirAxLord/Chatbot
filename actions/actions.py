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
        
        # Cargar datos desde el archivo JSON
        with open('data/plan_estudios.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        carrera = "Ingeniería en Sistemas Computacionales"  # Por defecto o puedes obtenerlo del tracker
        
        # Buscar la carrera en el dataset
        plan = None
        for c in data['carreras']:
            if c['nombre'] == carrera:
                plan = c
                break
        
        if plan:
            # Crear mensaje con la información del plan de estudios
            materias_por_semestre = {}
            for materia in plan['materias']:
                semestre = materia['semestre']
                if semestre not in materias_por_semestre:
                    materias_por_semestre[semestre] = []
                materias_por_semestre[semestre].append(materia['nombre'])
            
            mensaje = f"Plan de estudios de {carrera} ({plan['duracion']}):\n\n"
            for semestre in sorted(materias_por_semestre.keys()):
                mensaje += f"Semestre {semestre}: {', '.join(materias_por_semestre[semestre])}\n"
            
            dispatcher.utter_message(text=mensaje)
        else:
            dispatcher.utter_message(text="Lo siento, no encuentro información sobre esa carrera.")
        
        return []

class ActionProvidePrerequisitos(Action):
    def name(self) -> Text:
        return "action_provide_prerequisitos"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obtener la materia de la que el usuario está preguntando
        materia = tracker.get_slot("materia")
        
        # Cargar datos desde el archivo JSON
        with open('data/plan_estudios.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Buscar la materia en el dataset
        for carrera in data['carreras']:
            for m in carrera['materias']:
                if m['nombre'].lower() == materia.lower():
                    # Encontramos la materia
                    if m['prerequisitos']:
                        dispatcher.utter_message(text=f"Para cursar {m['nombre']} necesitas haber aprobado: {', '.join(m['prerequisitos'])}")
                    else:
                        dispatcher.utter_message(text=f"{m['nombre']} no tiene prerequisitos.")
                    return []
        
        dispatcher.utter_message(text=f"No encuentro información sobre la materia {materia}.")
        return []