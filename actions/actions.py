# actions.py - Archivo actualizado con ActionListMateriasInArea

import json
import unicodedata
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import os
from rapidfuzz import fuzz # Asegúrate de tener rapidfuzz en tu requirements.txt

# --- Función para normalizar texto ---
def normalize_text(text: Text) -> Text:
    """
    Elimina acentos y convierte el texto a minúsculas y le quita espacios extra.
    """
    if not isinstance(text, str):
        print(f"WARNING: normalize_text recibió un input no string: {text}")
        return ""

    normalized = unicodedata.normalize("NFKD", text)
    processed_text = normalized.encode("ascii", errors="ignore").decode("utf-8").lower()
    processed_text = ' '.join(processed_text.split())
    return processed_text

# Definimos un umbral de similitud para considerar que dos cadenas "coinciden"
SIMILARITY_THRESHOLD =75 # Ajusta este valor según necesites

# --- Función para cargar los datos del plan de estudios ---
def load_plan_estudios_data() -> Dict[Text, Any]:
    """
    Carga los datos del plan de estudios desde el archivo JSON.
    Retorna el diccionario con los datos o None si hay un error.
    """
    plan_estudios_path = os.path.join('data', 'plan_estudios.json')
    try:
        with open(plan_estudios_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        print(f"ERROR: El archivo {plan_estudios_path} no fue encontrado.")
        return None
    except json.JSONDecodeError:
        print(f"ERROR: Error al decodificar el JSON en {plan_estudios_path}.")
        return None
    except Exception as e:
        print(f"ERROR inesperado al cargar {plan_estudios_path}: {e}")
        return None

# --- Función para encontrar una materia por nombre o clave usando fuzzy matching ---
def find_materia_by_name_or_clave(data: Dict[Text, Any], materia_identifier: Text) -> Dict[Text, Any] | None:
    """
    Busca una materia en los datos del plan de estudios usando fuzzy matching
    con el nombre o comparando la clave.
    Retorna el objeto materia encontrado o None.
    """
    if not data or not materia_identifier:
        return None

    if not isinstance(materia_identifier, str):
        print(f"WARNING: find_materia_by_name_or_clave recibió un identificador no string: {materia_identifier}")
        try:
            materia_identifier_str = str(materia_identifier)
        except:
            return None
    else:
        materia_identifier_str = materia_identifier

    materia_identifier_normalizado = normalize_text(materia_identifier_str)
    mejor_similitud = 0
    materia_encontrada = None

    for carrera in data.get('carreras', []):
        for materia in carrera.get('materias', []):
            nombre_materia = materia.get('nombre', '')
            clave_materia = materia.get('clave_materia', '')

            # Comparación flexible con el nombre
            if nombre_materia:
                nombre_materia_normalizado = normalize_text(nombre_materia)
                similitud_nombre = fuzz.ratio(materia_identifier_normalizado, nombre_materia_normalizado)

                if similitud_nombre > mejor_similitud and similitud_nombre >= SIMILARITY_THRESHOLD:
                    mejor_similitud = similitud_nombre
                    materia_encontrada = materia
                    # No salimos aún para encontrar la mejor coincidencia global

            # Comparación exacta con la clave (si el identificador parece una clave)
            if clave_materia: # Solo intentamos normalizar si clave_materia existe
                 clave_materia_normalizada = normalize_text(clave_materia)
                 if materia_identifier_normalizado == clave_materia_normalizada:
                   return materia


    if materia_encontrada and mejor_similitud >= SIMILARITY_THRESHOLD:
        print(f"DEBUG find_materia: Encontrada la mejor coincidencia con similitud {mejor_similitud}: {materia_encontrada.get('nombre')}")
        return materia_encontrada

    print(f"DEBUG find_materia: No se encontró materia con similitud >= {SIMILARITY_THRESHOLD} para '{materia_identifier}'. Mejor similitud encontrada: {mejor_similitud}")
    return None

# --- Función para encontrar un area por nombre usando fuzzy matching (NUEVA FUNCIÓN DE AYUDA) ---
def find_area_by_name(data: Dict[Text, Any], area_name_identifier: Text) -> Dict[Text, Any] | None:
    """
    Busca un area de enfasis en los datos del plan de estudios usando fuzzy matching.
    Retorna el objeto area encontrado o None.
    """
    if not data or not area_name_identifier:
        return None

    if not isinstance(area_name_identifier, str):
        print(f"WARNING: find_area_by_name recibió un identificador no string: {area_name_identifier}")
        try:
            area_name_identifier_str = str(area_name_identifier)
        except:
            return None
    else:
        area_name_identifier_str = area_name_identifier

    area_name_identifier_normalizado = normalize_text(area_name_identifier_str)
    mejor_similitud = 0
    area_encontrada = None

    # Asumimos que las áreas están dentro de las carreras
    for carrera in data.get('carreras', []):
        for area in carrera.get('areas_enfasis', []):
            nombre_area = area.get('nombre', '')

            if nombre_area:
                nombre_area_normalizado = normalize_text(nombre_area)
                similitud = fuzz.ratio(area_name_identifier_normalizado, nombre_area_normalizado)

                if similitud > mejor_similitud and similitud >= SIMILARITY_THRESHOLD: # Usamos el mismo umbral
                    mejor_similitud = similitud
                    area_encontrada = area
                    # No salimos para encontrar la mejor coincidencia global

    if area_encontrada and mejor_similitud >= SIMILARITY_THRESHOLD:
        print(f"DEBUG find_area: Encontrada mejor coincidencia para '{area_name_identifier}' con similitud {mejor_similitud}: {area_encontrada.get('nombre')}")
        return area_encontrada

    print(f"DEBUG find_area: No se encontró area con similitud >= {SIMILARITY_THRESHOLD} para '{area_name_identifier}'. Mejor similitud: {mejor_similitud}")
    return None


# --- Funciones de ayuda para formatear datos de materia ---
def format_prerequisitos(prerequisitos_list: List[Dict[Text, Any]]) -> Text:
    """
    Formatea la lista de objetos de prerequisitos a un texto legible.
    """
    if not prerequisitos_list:
        return "no tiene prerequisitos"

    formatted_prereqs = []
    for prereq in prerequisitos_list:
        tipo = prereq.get('tipo')
        if tipo == 'materia':
            nombre_materia = prereq.get('nombre')
            if nombre_materia:
                formatted_prereqs.append(nombre_materia)
        elif tipo == 'creditos_totales_aprobados':
             valor = prereq.get('valor')
             if valor is not None:
                 formatted_prereqs.append(f"{valor} créditos aprobados")
        # Añadir lógica para otros tipos de prerequisitos si existen

    if not formatted_prereqs:
         return "tiene prerequisitos no especificados claramente."

    return ", ".join(formatted_prereqs)


# --- Acciones Personalizadas ---

class ActionProvidePlanEstudios(Action):
    def name(self) -> Text:
        return "action_provide_plan_estudios"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        data = load_plan_estudios_data()
        if not data:
            dispatcher.utter_message(text="Hubo un error al cargar la información del plan de estudios.")
            return []

        carrera_nombre = "Ingenieria en Sistemas Inteligentes" # Hardcodeado por ahora

        carrera_encontrada = next(
            (c for c in data.get('carreras', []) if c.get('nombre') == carrera_nombre),
            None
        )

        if not carrera_encontrada:
            dispatcher.utter_message(text=f"Lo siento, no encontré información sobre la carrera '{carrera_nombre}'.")
            return []

        materias_por_semestre = {}
        for materia in carrera_encontrada.get('materias', []):
            semestre = materia.get('semestre')
            nombre_materia = materia.get('nombre')
            if semestre is not None and nombre_materia:
                materias_por_semestre.setdefault(semestre, []).append(nombre_materia)

        semestres_ordenados = sorted(materias_por_semestre.keys())

        if not semestres_ordenados:
            dispatcher.utter_message(text=f"No se encontraron materias para la carrera '{carrera_nombre}'.")
            return []

        mensaje = f"Plan de estudios de {carrera_nombre} ({carrera_encontrada.get('duracion', 'duración no especificada')}):"

        for semestre in semestres_ordenados:
            materias_por_semestre[semestre].sort()
            mensaje += f"\nSemestre {semestre}: {', '.join(materias_por_semestre[semestre])}"

        dispatcher.utter_message(text=mensaje)

        return []

class ActionProvidePrerequisitos(Action):
    def name(self) -> Text:
        return "action_provide_prerequisitos"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        data = load_plan_estudios_data()
        if not data:
            dispatcher.utter_message(text="Hubo un error al cargar los datos del plan de estudios.")
            return []

        materia_slot = tracker.get_slot("materia")
        print(f"DEBUG ActionProvidePrerequisitos: materia_slot obtenido por NLU: '{materia_slot}'")

        if not materia_slot:
            dispatcher.utter_message(text="No pude identificar la materia de la que quieres saber los prerequisitos. ¿De qué materia se trata?")
            print("DEBUG ActionProvidePrerequisitos: Slot 'materia' vacío, pidiendo aclaración.")
            return []

        materia_encontrada = find_materia_by_name_or_clave(data, materia_slot)

        if not materia_encontrada:
            dispatcher.utter_message(text=f"No encontré información sobre la materia '{materia_slot}'. ¿Podrías especificar un poco más?")
            print(f"DEBUG ActionProvidePrerequisitos: Ninguna materia en JSON alcanzó el umbral de similitud con '{materia_slot}'.")
            return []

        nombre_materia = materia_encontrada.get('nombre', 'la materia')
        prerequisitos_list = materia_encontrada.get('prerequisitos', [])

        prerequisitos_texto = format_prerequisitos(prerequisitos_list)

        if "no tiene prerequisitos" in prerequisitos_texto:
            dispatcher.utter_message(text=f"La materia {nombre_materia} {prerequisitos_texto}.")
        elif "tiene prerequisitos no especificados" in prerequisitos_texto:
            dispatcher.utter_message(text=f"La materia {nombre_materia} {prerequisitos_texto}.")
        else:
            dispatcher.utter_message(text=f"Para cursar {nombre_materia} necesitas haber aprobado: {prerequisitos_texto}.")

        return []

class ActionListAreasEnfasis(Action):
    def name(self) -> Text:
        return "action_list_areas_enfasis"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        data = load_plan_estudios_data()
        if not data:
            dispatcher.utter_message(text="Hubo un error al cargar la información del plan de estudios.")
            return []

        carrera_nombre = "Ingenieria en Sistemas Inteligentes" # Hardcodeado por ahora

        carrera_encontrada = next(
            (c for c in data.get('carreras', []) if c.get('nombre') == carrera_nombre),
            None
        )

        if not carrera_encontrada:
            dispatcher.utter_message(text=f"Lo siento, no encontré información sobre la carrera '{carrera_nombre}'.")
            return []

        areas = carrera_encontrada.get('areas_enfasis', [])

        if not areas:
            dispatcher.utter_message(text=f"La carrera de {carrera_nombre} no tiene áreas de énfasis definidas.")
            return []

        mensaje = f"Las áreas de énfasis en la carrera de {carrera_nombre} son:"
        for area in areas:
            nombre_area = area.get('nombre', 'Área sin nombre')
            descripcion_area = area.get('descripcion', '')
            mensaje += f"\n- {nombre_area}"
            if descripcion_area:
                mensaje += f": {descripcion_area}"

        dispatcher.utter_message(text=mensaje)

        return []

# --- NUEVA CLASE DE ACCIÓN: ActionListMateriasInArea ---
class ActionListMateriasInArea(Action):
    def name(self) -> Text:
        return "action_list_materias_in_area"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        data = load_plan_estudios_data()
        if not data:
            dispatcher.utter_message(text="Hubo un error al cargar la información del plan de estudios.")
            return []

        # 1. Obtener el slot "area_enfasis".
        area_slot = tracker.get_slot("area_enfasis")
        print(f"DEBUG ActionListMateriasInArea: area_slot obtenido por NLU: '{area_slot}'")

        # **Verificar si el slot area_enfasis tiene un valor.**
        if not area_slot:
            dispatcher.utter_message(text="No pude identificar el área de énfasis. ¿De qué área te gustaría saber las materias?")
            print("DEBUG ActionListMateriasInArea: Slot 'area_enfasis' vacío, pidiendo aclaración.")
            return []

        # 2. Buscar el área de énfasis usando fuzzy matching
        area_encontrada = find_area_by_name(data, area_slot)

        if not area_encontrada:
            # Si no se encontró ningún área con suficiente similitud
            dispatcher.utter_message(text=f"No encontré el área de énfasis '{area_slot}'. ¿Podrías especificar el nombre del área?")
            print(f"DEBUG ActionListMateriasInArea: Ningún área en JSON alcanzó el umbral de similitud con '{area_slot}'.")
            return []

        # 3. Obtener la lista de claves de materias del área encontrada
        materias_clave_en_area = area_encontrada.get('materias_clave', [])
        nombre_area = area_encontrada.get('nombre', 'el área seleccionada')

        if not materias_clave_en_area:
            dispatcher.utter_message(text=f"El área '{nombre_area}' no tiene materias asociadas en este momento.")
            print(f"DEBUG ActionListMateriasInArea: El área '{nombre_area}' no tiene 'materias_clave' definidas.")
            return []

        # 4. Buscar los nombres de las materias usando las claves
        materias_encontradas = []
        # Para eficiencia, podrías crear un diccionario {clave: materia_obj} al cargar el JSON
        # Pero por ahora, iteramos sobre todas las materias para encontrar las que coincidan con las claves del área
        for carrera in data.get('carreras', []):
             for materia in carrera.get('materias', []):
                 clave = materia.get('clave_materia')
                 nombre = materia.get('nombre')
                 if clave and nombre and clave in materias_clave_en_area:
                     materias_encontradas.append(nombre)

        if not materias_encontradas:
             dispatcher.utter_message(text=f"No se encontraron detalles para las materias listadas en el área '{nombre_area}'.")
             print(f"DEBUG ActionListMateriasInArea: No se encontraron materias principales con las claves: {materias_clave_en_area}")
             return []

        # Ordenamos las materias alfabéticamente para presentarlas
        materias_encontradas.sort()

        # 5. Formatear y enviar la respuesta
        mensaje = f"Las materias en el área de '{nombre_area}' son:\n- {', '.join(materias_encontradas)}"

        dispatcher.utter_message(text=mensaje)

        return []

# actions.py - Añade esta nueva clase de acción al final del archivo

class ActionProvideMateriaDetails(Action):
    def name(self) -> Text:
        return "action_provide_materia_details"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Cargar los datos del plan de estudios (reutilizamos la función)
        data = load_plan_estudios_data()
        if not data:
            dispatcher.utter_message(text="Hubo un error al cargar la información del plan de estudios.")
            return []

        # 1. Obtener el slot "materia". El NLU debe llenarlo.
        materia_slot = tracker.get_slot("materia")
        print(f"DEBUG ActionProvideMateriaDetails: materia_slot obtenido por NLU: '{materia_slot}'")

        # **Verificar si el slot materia tiene un valor.**
        # Si el NLU no logró extraer la entidad 'materia', el slot estará vacío (None).
        if not materia_slot:
            dispatcher.utter_message(text="No pude identificar la materia de la que quieres saber detalles. ¿De qué materia se trata?")
            print("DEBUG ActionProvideMateriaDetails: Slot 'materia' vacío, pidiendo aclaración.")
            return []

        # 2. Buscar la materia usando fuzzy matching (reutilizamos la función)
        materia_encontrada = find_materia_by_name_or_clave(data, materia_slot)

        # Si no se encontró ninguna materia con suficiente similitud (usando el umbral)
        if not materia_encontrada:
            dispatcher.utter_message(text=f"No encontré información sobre la materia '{materia_slot}'. ¿Podrías especificar un poco más?")
            print(f"DEBUG ActionProvideMateriaDetails: Ninguna materia en JSON alcanzó el umbral de similitud con '{materia_slot}'.")
            return []

        # 3. Recuperar los detalles de la materia encontrada
        nombre_materia = materia_encontrada.get('nombre', 'la materia seleccionada')
        objetivo = materia_encontrada.get('objetivo', '') # Obtiene el objetivo, string vacío si no existe
        contenido_resumen = materia_encontrada.get('contenido_tematico_resumen', '') # Obtiene el resumen, string vacío si no existe

        # 4. Formatear y enviar la respuesta
        mensaje = f"Aquí tienes detalles sobre la materia '{nombre_materia}':\n"

        # Añadimos la información solo si existe en el JSON
        if objetivo:
            mensaje += f"\n**Objetivo:** {objetivo}\n" # Usamos Markdown para formatear

        if contenido_resumen:
            mensaje += f"\n**Contenido Temático (Resumen):** {contenido_resumen}\n" # Usamos Markdown

        # Mensaje de fallback si no se encontró ni objetivo ni contenido
        if not objetivo and not contenido_resumen:
            mensaje += "No se encontró información detallada (objetivo o contenido) para esta materia en este momento."

        dispatcher.utter_message(text=mensaje)

        return []

# Recuerda añadir más acciones aquí para otras funcionalidades!
# action_list_career_outcomes
# action_list_materias_in_area (si aún no la has completado)
# action_provide_materia_hours
# etc.