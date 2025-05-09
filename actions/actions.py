# actions.py - Archivo completo con Fuzzy Matching y verificación de slot

import json
import unicodedata# Para normalizar textos (quitar acentos, etc.)
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import os
# Importamos la función fuzz para comparación flexible
from rapidfuzz import fuzz # Asegúrate de tener rapidfuzz en tu requirements.txt

# Definimos un umbral de similitud para considerar que dos cadenas "coinciden"
# Puedes ajustar este valor (0 a 100). 80 suele ser un buen punto de partida.
SIMILARITY_THRESHOLD = 85

def normalize_text(text: Text) -> Text:

    normalized = unicodedata.normalize("NFKD", text)
    # Eliminamos acentos y convertimos a minúsculas
    processed_text = normalized.encode("ascii", errors="ignore").decode("utf-8").lower()
    # Opcional: Quitar espacios al inicio y final y reemplazar múltiples espacios por uno solo
    processed_text = ' '.join(processed_text.split())
    return processed_text


class ActionProvidePlanEstudios(Action):
    def name(self) -> Text:
        return "action_provide_plan_estudios"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Construimos la ruta al archivo JSON usando la ruta del directorio de trabajo /app
        # Esto es más robusto ya que sabemos que /app es el WORKDIR y el punto de montaje del volumen
        plan_estudios_path = os.path.join('data', 'plan_estudios.json')

        try:
            # Usamos la ruta construida
            with open(plan_estudios_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            dispatcher.utter_message(text="Hubo un error al cargar el plan de estudios.")
            print(f"ERROR al cargar plan_estudios.json en ActionProvidePlanEstudios: {e}")
            return []

        # Definir la carrera a buscar (Considera hacer esto dinámico en el futuro)
        carrera = "Ingeniería en Sistemas Computacionales"

        # Se compara de forma exacta (sin normalización en esta versión de búsqueda de carrera)
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

        materia_slot = tracker.get_slot("materia")

        print(f"DEBUG ActionProvidePrerequisitos: materia_slot obtenido por NLU: '{materia_slot}'")


        if not materia_slot:
            # Si el slot está vacío, pedir al usuario que aclare y terminar la acción.
            dispatcher.utter_message(text="No pude identificar la materia de la que quieres saber los prerequisitos. ¿De qué materia se trata?")
            print("DEBUG ActionProvidePrerequisitos: Slot 'materia' vacío, pidiendo aclaración.")
            return [] # ¡Importante! Salir de la función run si el slot está vacío.


        # Si llegamos aquí, significa que materia_slot NO está vacío.
        # Normalizamos el valor del slot para la comparación flexible.
        materia_usuario_normalizada = normalize_text(materia_slot)
        print(f"DEBUG ActionProvidePrerequisitos: Materia del slot normalizada: '{materia_usuario_normalizada}'")


        # 2. Abrir y cargar el archivo JSON con el plan de estudios
        plan_estudios_path = os.path.join('data', 'plan_estudios.json')

        try:
            with open(plan_estudios_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            dispatcher.utter_message(text="Hubo un error al cargar los datos del plan de estudios.")
            print(f"ERROR al cargar plan_estudios.json en ActionProvidePrerequisitos: {e}")
            return []

         # 3. Buscar la materia usando Fuzzy Matching
        materia_encontrada = None
        mejor_similitud = 0
        nombre_materia_en_json = None # Para guardar el nombre exacto encontrado en el JSON

        for carrera in data['carreras']:
            for m in carrera['materias']:
                # Normalizamos el nombre de la materia del JSON para la comparación
                nombre_materia_json_normalizado = normalize_text(m['nombre'])

                # Calculamos la similitud entre el texto del usuario y el nombre de la materia en el JSON
                # Usamos fuzz.ratio o fuzz.partial_ratio. Partial_ratio es útil si la entidad extraída es solo una parte del nombre completo.
                # Aquí usamos ratio para una comparación más global, pero puedes experimentar.
                similitud = fuzz.ratio(materia_usuario_normalizada, nombre_materia_json_normalizado)

                print(f"DEBUG ActionProvidePrerequisitos: Comparando '{materia_usuario_normalizada}' con '{nombre_materia_json_normalizado}' -> Similitud: {similitud}")

                # Si encontramos una similitud que supera el umbral y es la mejor hasta ahora
                if similitud > mejor_similitud and similitud >= SIMILARITY_THRESHOLD:
                    mejor_similitud = similitud
                    materia_encontrada = m
                    nombre_materia_en_json = m['nombre'] # Guardamos el nombre original del JSON
                    # break # No salimos con break aquí para encontrar la mejor coincidencia posible en todas las materias


        if not materia_encontrada:
            # Si después de revisar todas las materias, no encontramos una con suficiente similitud
            dispatcher.utter_message(text=f"No encontré información sobre la materia '{materia_slot}'. ¿Podrías especificar un poco más?")
            print(f"DEBUG ActionProvidePrerequisitos: Ninguna materia en JSON alcanzó el umbral de similitud con '{materia_usuario_normalizada}'. Mejor similitud encontrada: {mejor_similitud}")
            return []

        # 4. Responder mostrando los prerequisitos (si existen) o indicar que no tiene
        # Usamos el nombre exacto de la materia encontrada en el JSON para la respuesta
        prerequisitos = materia_encontrada.get('prerequisitos', [])
        if prerequisitos:
            prereq_list = ', '.join(prerequisitos)
            dispatcher.utter_message(text=f"Para cursar {nombre_materia_en_json} necesitas haber aprobado: {prereq_list}.")
        else:
            dispatcher.utter_message(text=f"{nombre_materia_en_json} no tiene prerequisitos.")

        return []