import json
import unicodedata
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet 
import os
from rapidfuzz import fuzz 

SIMILARITY_THRESHOLD = 75 

def normalize_text(text: Text) -> Text:
    if not isinstance(text, str):
        return "" 

    normalized = unicodedata.normalize("NFKD", text)
    processed_text = normalized.encode("ascii", errors="ignore").decode("utf-8").lower()
    processed_text = ' '.join(processed_text.split())
    return processed_text

def load_plan_estudios_data() -> Dict[Text, Any] | None:
    plan_estudios_path = os.path.join('data', 'plan_estudios.json') 
    try:
        with open(plan_estudios_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        print(f"ERROR CRÍTICO: El archivo del plan de estudios '{plan_estudios_path}' no fue encontrado.")
        return None
    except json.JSONDecodeError:
        print(f"ERROR CRÍTICO: Error al decodificar el JSON en '{plan_estudios_path}'. Verifica su formato.")
        return None
    except Exception as e:
        print(f"ERROR CRÍTICO inesperado al cargar '{plan_estudios_path}': {e}")
        return None

# Cargamos los datos una vez globalmente para eficiencia.
PLAN_ESTUDIOS_DATA = load_plan_estudios_data()

def find_materia_by_name_or_clave(materia_identifier: Text) -> Dict[Text, Any] | None:
    if not PLAN_ESTUDIOS_DATA or not materia_identifier:
        return None

    materia_identifier_str = str(materia_identifier)
    materia_identifier_normalizado = normalize_text(materia_identifier_str)
    mejor_similitud_nombre = 0
    materia_encontrada_por_nombre = None

    # Accedemos a la lista de carreras, luego a la primera carrera, y luego a sus materias
    if PLAN_ESTUDIOS_DATA.get('carreras') and len(PLAN_ESTUDIOS_DATA['carreras']) > 0:
        for materia in PLAN_ESTUDIOS_DATA['carreras'][0].get('materias', []):
            nombre_materia = materia.get('nombre', '')
            clave_materia = str(materia.get('clave_materia', ''))

            if clave_materia and materia_identifier_normalizado == normalize_text(clave_materia):
                return materia

            if nombre_materia:
                nombre_materia_normalizado = normalize_text(nombre_materia)
                similitud_nombre = fuzz.ratio(materia_identifier_normalizado, nombre_materia_normalizado)

                if similitud_nombre > mejor_similitud_nombre:
                    mejor_similitud_nombre = similitud_nombre
                    if similitud_nombre >= SIMILARITY_THRESHOLD:
                        materia_encontrada_por_nombre = materia
                        if similitud_nombre > 95:
                             return materia_encontrada_por_nombre
    else:
        print("ERROR: La estructura esperada 'carreras' no se encontró o está vacía en el JSON.")
        return None


    if materia_encontrada_por_nombre and mejor_similitud_nombre >= SIMILARITY_THRESHOLD:
        return materia_encontrada_por_nombre
    return None


def find_area_by_name(area_name_identifier: Text) -> Dict[Text, Any] | None:
    if not PLAN_ESTUDIOS_DATA or not area_name_identifier:
        return None

    area_name_identifier_str = str(area_name_identifier)
    area_name_identifier_normalizado = normalize_text(area_name_identifier_str)
    mejor_similitud = 0
    area_encontrada = None

    if PLAN_ESTUDIOS_DATA.get('carreras') and len(PLAN_ESTUDIOS_DATA['carreras']) > 0:
        for area in PLAN_ESTUDIOS_DATA['carreras'][0].get('areas_enfasis', []):
            nombre_area = area.get('nombre', '')
            if nombre_area:
                nombre_area_normalizado = normalize_text(nombre_area)
                similitud = fuzz.ratio(area_name_identifier_normalizado, nombre_area_normalizado)

                if similitud > mejor_similitud:
                    mejor_similitud = similitud
                    if similitud >= SIMILARITY_THRESHOLD:
                        area_encontrada = area
                        if similitud > 95:
                            return area_encontrada
    else:
        print("ERROR: La estructura esperada 'carreras' no se encontró o está vacía en el JSON.")
        return None

    if area_encontrada and mejor_similitud >= SIMILARITY_THRESHOLD:
        return area_encontrada
    return None

def format_prerequisitos(prerequisitos_list: List[Dict[Text, Any]]) -> Text:
    if not prerequisitos_list:
        return "no tiene prerequisitos especificados"

    formatted_prereqs = []
    for prereq in prerequisitos_list:
        tipo = prereq.get('tipo')
        nombre_materia_prereq = prereq.get('nombre')
        clave_materia_prereq = prereq.get('clave')

        if tipo == 'materia':
            if nombre_materia_prereq and clave_materia_prereq:
                formatted_prereqs.append(f"{nombre_materia_prereq} (Clave: {clave_materia_prereq})")
            elif nombre_materia_prereq:
                formatted_prereqs.append(nombre_materia_prereq)
            elif clave_materia_prereq:
                materia_info = find_materia_by_name_or_clave(str(clave_materia_prereq))
                if materia_info and materia_info.get('nombre'):
                    formatted_prereqs.append(f"{materia_info.get('nombre')} (Clave: {clave_materia_prereq})")
                else: 
                    formatted_prereqs.append(f"Materia con clave {clave_materia_prereq} (nombre no encontrado en lista principal)")

    if not formatted_prereqs: 
        return "tiene prerequisitos, pero no pude detallarlos."
    return ", ".join(formatted_prereqs)

class ActionProvidePlanEstudios(Action):
    def name(self) -> Text:
        return "action_provide_plan_estudios"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        if not PLAN_ESTUDIOS_DATA or not PLAN_ESTUDIOS_DATA.get('carreras'):
            dispatcher.utter_message(text="Lo siento, hubo un error al cargar la información del plan de estudios.")
            return []

        carrera_data = PLAN_ESTUDIOS_DATA['carreras'][0]
        carrera_nombre = carrera_data.get('nombre', "la carrera")
        duracion = carrera_data.get('duracion', 'duración no especificada')

        materias_por_semestre = {}
        # Iteramos sobre las materias definidas en el JSON
        for materia in carrera_data.get('materias', []):
            semestre = materia.get('semestre')
            nombre_materia = materia.get('nombre')
            if semestre is not None and nombre_materia:
                materias_por_semestre.setdefault(semestre, []).append(nombre_materia)

        if not materias_por_semestre:
            dispatcher.utter_message(text=f"No se encontraron materias de énfasis para {carrera_nombre}.")
            return []

        semestres_ordenados = sorted(materias_por_semestre.keys())
        mensaje = f"Las materias de énfasis para {carrera_nombre} ({duracion}) son:\n"
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

        if not PLAN_ESTUDIOS_DATA:
            dispatcher.utter_message(text="Lo siento, hubo un error al cargar los datos del plan de estudios.")
            return []

        materia_slot = tracker.get_slot("materia")
        if not materia_slot:
            dispatcher.utter_message(response="utter_pedir_materia_especifica")
            return []

        materia_encontrada = find_materia_by_name_or_clave(materia_slot)
        if not materia_encontrada:
            dispatcher.utter_message(response="utter_materia_no_encontrada")
            return []

        nombre_materia_actual = materia_encontrada.get('nombre', materia_slot)
        prerequisitos_list = materia_encontrada.get('prerequisitos', [])
        prerequisitos_texto = format_prerequisitos(prerequisitos_list)

        if "no tiene prerequisitos especificados" in prerequisitos_texto:
            dispatcher.utter_message(text=f"La materia '{nombre_materia_actual}' {prerequisitos_texto}.")
        else:
            dispatcher.utter_message(text=f"Para cursar '{nombre_materia_actual}', necesitas: {prerequisitos_texto}.")
        return []

class ActionListAreasEnfasis(Action):
    def name(self) -> Text:
        return "action_list_areas_enfasis"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        if not PLAN_ESTUDIOS_DATA or not PLAN_ESTUDIOS_DATA.get('carreras'):
            dispatcher.utter_message(text="Lo siento, hubo un error al cargar la información del plan de estudios.")
            return []

        carrera_data = PLAN_ESTUDIOS_DATA['carreras'][0]
        carrera_nombre = carrera_data.get('nombre', "esta carrera")
        areas = carrera_data.get('areas_enfasis', [])

        if not areas:
            dispatcher.utter_message(text=f"La carrera de {carrera_nombre} no parece tener áreas de énfasis definidas en mis datos.")
            return []

        nombres_areas = [area.get('nombre') for area in areas if area.get('nombre')]
        if not nombres_areas:
            dispatcher.utter_message(text=f"No encontré nombres para las áreas de énfasis de {carrera_nombre}.")
            return []

        mensaje = f"Las áreas de énfasis en {carrera_nombre} son:\n- " + "\n- ".join(nombres_areas)
        dispatcher.utter_message(text=mensaje)
        return []

class ActionListMateriasInArea(Action):
    def name(self) -> Text:
        return "action_list_materias_in_area"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        if not PLAN_ESTUDIOS_DATA:
            dispatcher.utter_message(text="Lo siento, hubo un error al cargar la información del plan de estudios.")
            return []

        area_slot = tracker.get_slot("area_enfasis")
        if not area_slot:
            dispatcher.utter_message(response="utter_pedir_area_especifica")
            return []

        area_encontrada = find_area_by_name(area_slot)
        if not area_encontrada:
            dispatcher.utter_message(response="utter_area_no_encontrada")
            return []

        nombre_area_actual = area_encontrada.get('nombre', area_slot)
        materias_clave_en_area = area_encontrada.get('materias_clave', [])

        if not materias_clave_en_area:
            dispatcher.utter_message(text=f"El área '{nombre_area_actual}' no tiene materias de énfasis listadas en este momento.")
            return []

        nombres_materias_en_area = []
        for clave_materia in materias_clave_en_area:
            materia_info = find_materia_by_name_or_clave(str(clave_materia))
            if materia_info and materia_info.get('nombre'):
                nombres_materias_en_area.append(materia_info.get('nombre'))

        if not nombres_materias_en_area:
            dispatcher.utter_message(text=f"No pude encontrar los detalles de las materias para el área '{nombre_area_actual}'.")
            return []

        nombres_materias_en_area.sort()
        mensaje = f"Las materias de énfasis en el área '{nombre_area_actual}' son:\n- " + "\n- ".join(nombres_materias_en_area)
        dispatcher.utter_message(text=mensaje)
        return []

class ActionProvideMateriaDetails(Action):
    def name(self) -> Text:
        return "action_provide_materia_details"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        if not PLAN_ESTUDIOS_DATA:
            dispatcher.utter_message(text="Lo siento, hubo un error al cargar la información del plan de estudios.")
            return []

        materia_slot = tracker.get_slot("materia")
        if not materia_slot:
            dispatcher.utter_message(response="utter_pedir_materia_especifica")
            return []

        materia_encontrada = find_materia_by_name_or_clave(materia_slot)
        if not materia_encontrada:
            dispatcher.utter_message(response="utter_materia_no_encontrada")
            return []

        nombre_materia_actual = materia_encontrada.get('nombre', materia_slot)
        objetivo = materia_encontrada.get('objetivo')
        contenido = materia_encontrada.get('contenido_tematico_resumen')
        clave = materia_encontrada.get('clave_materia', "N/A")
        semestre = materia_encontrada.get('semestre', "N/A")
        creditos = materia_encontrada.get('creditos', "N/A")
        tipo = materia_encontrada.get('tipo_materia')
        horas_s = materia_encontrada.get('horas_clase_semana')
        horas_t = materia_encontrada.get('horas_totales_semestre')
        prereqs = format_prerequisitos(materia_encontrada.get('prerequisitos', []))


        mensaje_partes = [f"Detalles de la materia de énfasis '{nombre_materia_actual}' (Clave: {clave}):"]
        if semestre != "N/A": mensaje_partes.append(f"- Semestre: {semestre}")
        if creditos != "N/A": mensaje_partes.append(f"- Créditos: {creditos}")
        if tipo: mensaje_partes.append(f"- Tipo: {tipo}")
        if horas_s is not None: mensaje_partes.append(f"- Horas/semana: {horas_s}")
        if horas_t is not None: mensaje_partes.append(f"- Horas totales/semestre: {horas_t}")
        if objetivo: mensaje_partes.append(f"- Objetivo: {objetivo}")
        if contenido: mensaje_partes.append(f"- Contenido (resumen): {contenido}")
        if prereqs and "no tiene prerequisitos especificados" not in prereqs : mensaje_partes.append(f"- Prerrequisitos: {prereqs}")
        elif not materia_encontrada.get('prerequisitos'): mensaje_partes.append(f"- Prerrequisitos: No tiene prerequisitos especificados.")


        if len(mensaje_partes) == 1:
            dispatcher.utter_message(text=f"No encontré detalles específicos como objetivo o contenido para '{nombre_materia_actual}', aparte de que es una materia de énfasis.")
        else:
            dispatcher.utter_message(text="\n".join(mensaje_partes))
        return []


class ActionInformarNombreCarrera(Action):
    def name(self) -> Text:
        return "action_informar_nombre_carrera"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        if not PLAN_ESTUDIOS_DATA or not PLAN_ESTUDIOS_DATA.get('carreras'):
            dispatcher.utter_message(text="Lo siento, no pude cargar la información de la carrera en este momento.")
            return []

        carrera_data = PLAN_ESTUDIOS_DATA['carreras'][0]
        nombre_carrera = carrera_data.get("nombre")

        if nombre_carrera:
            dispatcher.utter_message(text=f"La carrera sobre la que te puedo informar es: {nombre_carrera}.")
        else:
            dispatcher.utter_message(response="utter_info_no_disponible")
        return []

class ActionInformarDuracionCarrera(Action):
    def name(self) -> Text:
        return "action_informar_duracion_carrera"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        if not PLAN_ESTUDIOS_DATA or not PLAN_ESTUDIOS_DATA.get('carreras'):
            dispatcher.utter_message(text="Lo siento, no pude cargar la información de la carrera en este momento.")
            return []

        carrera_data = PLAN_ESTUDIOS_DATA['carreras'][0]
        duracion_carrera = carrera_data.get("duracion")
        nombre_carrera = carrera_data.get("nombre", "esta carrera")

        if duracion_carrera:
            dispatcher.utter_message(text=f"La duración de {nombre_carrera} es de {duracion_carrera}.")
        else:
            dispatcher.utter_message(text=f"No encontré información sobre la duración de {nombre_carrera}.")
        return []

class ActionInformarResultadosProfesionales(Action):
    def name(self) -> Text:
        return "action_informar_resultados_profesionales"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        if not PLAN_ESTUDIOS_DATA or not PLAN_ESTUDIOS_DATA.get('carreras'):
            dispatcher.utter_message(text="Lo siento, no pude cargar la información de la carrera en este momento.")
            return []

        carrera_data = PLAN_ESTUDIOS_DATA['carreras'][0]
        resultados = carrera_data.get("resultados_profesionales")
        nombre_carrera = carrera_data.get("nombre", "esta carrera")

        if resultados and isinstance(resultados, list) and len(resultados) > 0:
            mensaje = f"Algunos de los roles profesionales y resultados al egresar de {nombre_carrera} son:\n"
            for rol in resultados:
                mensaje += f"- {rol}\n"
            dispatcher.utter_message(text=mensaje.strip())
        elif resultados is not None:
             dispatcher.utter_message(text=f"No hay resultados profesionales listados específicamente para {nombre_carrera} en este momento.")
        else:
            dispatcher.utter_message(text=f"No encontré información clara sobre los resultados profesionales para {nombre_carrera}.")
        return []

class ActionInformarDescripcionAreaEnfasis(Action):
    def name(self) -> Text:
        return "action_informar_descripcion_area_enfasis"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        if not PLAN_ESTUDIOS_DATA:
            dispatcher.utter_message(text="Lo siento, hubo un error al cargar la información.")
            return []

        area_slot = tracker.get_slot("area_enfasis")
        if not area_slot:
            dispatcher.utter_message(response="utter_pedir_area_especifica")
            return []

        area_encontrada = find_area_by_name(area_slot)
        if not area_encontrada:
            dispatcher.utter_message(response="utter_area_no_encontrada")
            return []

        nombre_area_actual = area_encontrada.get('nombre', area_slot)
        descripcion = area_encontrada.get("descripcion")

        if descripcion:
            dispatcher.utter_message(text=f"El área de énfasis '{nombre_area_actual}' se enfoca en: {descripcion}")
        else:
            dispatcher.utter_message(text=f"No tengo una descripción detallada para el área '{nombre_area_actual}' en este momento.")
        return []

class ActionInformarObjetivoMateria(Action):
    def name(self) -> Text:
        return "action_informar_objetivo_materia"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        if not PLAN_ESTUDIOS_DATA:
            dispatcher.utter_message(text="Lo siento, hubo un error al cargar la información.")
            return []
        materia_slot = tracker.get_slot("materia")
        if not materia_slot:
            dispatcher.utter_message(response="utter_pedir_materia_especifica")
            return []
        materia_encontrada = find_materia_by_name_or_clave(materia_slot)
        if not materia_encontrada:
            dispatcher.utter_message(response="utter_materia_no_encontrada")
            return []
        nombre_materia = materia_encontrada.get('nombre', materia_slot)
        objetivo = materia_encontrada.get("objetivo")
        if objetivo:
            dispatcher.utter_message(text=f"El objetivo de '{nombre_materia}' es: {objetivo}")
        else:
            dispatcher.utter_message(text=f"No encontré un objetivo específico para la materia '{nombre_materia}'.")
        return []

class ActionInformarCreditosMateria(Action):
    def name(self) -> Text:
        return "action_informar_creditos_materia"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        if not PLAN_ESTUDIOS_DATA:
            dispatcher.utter_message(text="Lo siento, hubo un error al cargar la información.")
            return []
        materia_slot = tracker.get_slot("materia")
        if not materia_slot:
            dispatcher.utter_message(response="utter_pedir_materia_especifica")
            return []
        materia_encontrada = find_materia_by_name_or_clave(materia_slot)
        if not materia_encontrada:
            dispatcher.utter_message(response="utter_materia_no_encontrada")
            return []
        nombre_materia = materia_encontrada.get('nombre', materia_slot)
        creditos = materia_encontrada.get("creditos")
        if creditos is not None:
            dispatcher.utter_message(text=f"La materia '{nombre_materia}' tiene {creditos} créditos.")
        else:
            dispatcher.utter_message(text=f"No encontré la información de créditos para '{nombre_materia}'.")
        return []

class ActionInformarSemestreMateria(Action):
    def name(self) -> Text:
        return "action_informar_semestre_materia"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        if not PLAN_ESTUDIOS_DATA:
            dispatcher.utter_message(text="Lo siento, hubo un error al cargar la información.")
            return []
        materia_slot = tracker.get_slot("materia")
        if not materia_slot:
            dispatcher.utter_message(response="utter_pedir_materia_especifica")
            return []
        materia_encontrada = find_materia_by_name_or_clave(materia_slot)
        if not materia_encontrada:
            dispatcher.utter_message(response="utter_materia_no_encontrada")
            return []
        nombre_materia = materia_encontrada.get('nombre', materia_slot)
        semestre = materia_encontrada.get("semestre")
        if semestre is not None:
            dispatcher.utter_message(text=f"La materia '{nombre_materia}' usualmente se cursa en el {semestre}º semestre.")
        else:
            dispatcher.utter_message(text=f"No encontré información sobre el semestre para '{nombre_materia}'.")
        return []

class ActionInformarHorasMateria(Action):
    def name(self) -> Text:
        return "action_informar_horas_materia"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        if not PLAN_ESTUDIOS_DATA:
            dispatcher.utter_message(text="Lo siento, hubo un error al cargar la información.")
            return []
        materia_slot = tracker.get_slot("materia")
        if not materia_slot:
            dispatcher.utter_message(response="utter_pedir_materia_especifica")
            return []
        materia_encontrada = find_materia_by_name_or_clave(materia_slot)
        if not materia_encontrada:
            dispatcher.utter_message(response="utter_materia_no_encontrada")
            return []

        nombre_materia = materia_encontrada.get('nombre', materia_slot)
        horas_semana = materia_encontrada.get("horas_clase_semana")
        horas_semestre = materia_encontrada.get("horas_totales_semestre")
        respuesta_partes = [f"Para la materia '{nombre_materia}':"]
        info_encontrada = False

        if horas_semana is not None:
            respuesta_partes.append(f"- Horas de clase por semana: {horas_semana}")
            info_encontrada = True
        if horas_semestre is not None:
            respuesta_partes.append(f"- Horas totales en el semestre: {horas_semestre}")
            info_encontrada = True

        if info_encontrada:
            dispatcher.utter_message(text="\n".join(respuesta_partes))
        else:
            dispatcher.utter_message(text=f"No encontré información sobre las horas para la materia '{nombre_materia}'.")
        return []

class ActionInformarTipoMateria(Action):
    def name(self) -> Text:
        return "action_informar_tipo_materia"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        if not PLAN_ESTUDIOS_DATA:
            dispatcher.utter_message(text="Lo siento, hubo un error al cargar la información.")
            return []
        materia_slot = tracker.get_slot("materia")
        if not materia_slot:
            dispatcher.utter_message(response="utter_pedir_materia_especifica")
            return []
        materia_encontrada = find_materia_by_name_or_clave(materia_slot)
        if not materia_encontrada:
            dispatcher.utter_message(response="utter_materia_no_encontrada")
            return []
        nombre_materia = materia_encontrada.get('nombre', materia_slot)
        tipo = materia_encontrada.get("tipo_materia")
        if tipo:
            dispatcher.utter_message(text=f"La materia '{nombre_materia}' es de tipo: {tipo}.")
        else:
            dispatcher.utter_message(text=f"No encontré información sobre el tipo para la materia '{nombre_materia}'.")
        return []

class ActionInformarContenidoMateria(Action):
    def name(self) -> Text:
        return "action_informar_contenido_materia"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        if not PLAN_ESTUDIOS_DATA:
            dispatcher.utter_message(text="Lo siento, hubo un error al cargar la información.")
            return []
        materia_slot = tracker.get_slot("materia")
        if not materia_slot:
            dispatcher.utter_message(response="utter_pedir_materia_especifica")
            return []
        materia_encontrada = find_materia_by_name_or_clave(materia_slot)
        if not materia_encontrada:
            dispatcher.utter_message(response="utter_materia_no_encontrada")
            return []
        nombre_materia = materia_encontrada.get('nombre', materia_slot)
        contenido = materia_encontrada.get("contenido_tematico_resumen")
        if contenido:
            dispatcher.utter_message(text=f"El contenido temático resumido de '{nombre_materia}' incluye: {contenido}")
        else:
            dispatcher.utter_message(text=f"No encontré un resumen del contenido temático para '{nombre_materia}'.")
        return []

class ActionInformarClaveMateria(Action):
    def name(self) -> Text:
        return "action_informar_clave_materia"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        if not PLAN_ESTUDIOS_DATA:
            dispatcher.utter_message(text="Lo siento, hubo un error al cargar la información.")
            return []
        materia_slot = tracker.get_slot("materia")
        if not materia_slot:
            dispatcher.utter_message(response="utter_pedir_materia_especifica")
            return []
        materia_encontrada = find_materia_by_name_or_clave(materia_slot)
        if not materia_encontrada:
            dispatcher.utter_message(response="utter_materia_no_encontrada")
            return []

        nombre_materia = materia_encontrada.get('nombre', materia_slot)
        clave = materia_encontrada.get("clave_materia")
        if clave:
            dispatcher.utter_message(text=f"La clave de la materia '{nombre_materia}' es: {clave}.")
        else:
            dispatcher.utter_message(text=f"No encontré la clave para la materia '{nombre_materia}'.")
        return []

class ActionInformarNombreMateriaPorClave(Action):
    def name(self) -> Text:
        return "action_informar_nombre_materia_por_clave"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        if not PLAN_ESTUDIOS_DATA:
            dispatcher.utter_message(text="Lo siento, hubo un error al cargar la información.")
            return []
        materia_slot = tracker.get_slot("materia") 
        if not materia_slot:
            dispatcher.utter_message(text="Por favor, dime la clave de la materia para la que quieres saber el nombre.")
            return []

        materia_encontrada = find_materia_by_name_or_clave(materia_slot)

        if not materia_encontrada:
            dispatcher.utter_message(text=f"No encontré ninguna materia de énfasis con la clave '{materia_slot}'.")
            return []

        nombre_materia = materia_encontrada.get('nombre')
        clave_original = materia_slot

        if nombre_materia:
            dispatcher.utter_message(text=f"La materia de énfasis con clave '{clave_original}' se llama: {nombre_materia}.")
        else:
            dispatcher.utter_message(text=f"Encontré la clave '{clave_original}' pero no su nombre asociado.")
        return []