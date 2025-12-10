# 🚀 Chatbot Rasa con Docker

Este proyecto es un chatbot desarrollado con **Rasa** y ejecutado dentro de contenedores **Docker**, utilizando `Docker Compose`.

## 🧠 Descripción del Proyecto

Este chatbot está orientado a brindar información académica de la carrera de **Ingeniería en Sistemas Inteligentes** con foco en las **áreas de énfasis** y sus **materias clave**. Integra datos estructurados del archivo `data/plan_estudios.json` y expone respuestas a consultas frecuentes mediante acciones personalizadas en `actions/actions.py`.

### 🎯 ¿Qué puede hacer?
- Consultar el plan de estudios y materias por semestre.
- Listar áreas de énfasis disponibles (p. ej., IA y Robótica, Interacción y Videojuegos, Ciberseguridad, Desarrollo Web y Multiplataforma).
- Mostrar las materias asociadas a una área de énfasis.
- Dar detalles de una materia de énfasis: objetivo, contenidos, créditos, semestre, tipo, horas, prerrequisitos y clave.
- Responder información general de la carrera: nombre, duración y posibles resultados/roles profesionales.

### 🔍 Cómo funciona
- El NLU usa `data/nlu.yml` para identificar intenciones como `preguntar_plan_estudios`, `preguntar_prerequisitos`, `preguntar_areas_enfasis`, etc.
- La conversación se guía con `data/stories.yml` y `data/rules.yml`.
- Las respuestas y slots se definen en `domain.yml`.
- La lógica de negocio vive en `actions/actions.py`, que lee `data/plan_estudios.json` y realiza búsquedas tolerantes a errores tipográficos (RapidFuzz) para encontrar materias y áreas por nombre o clave.
- Se puede interactuar vía consola (`rasa shell`) o mediante la **interfaz web** (`index.html` + `script.js`).

## 🔧 Instrucciones de Instalación

### 1️⃣ Clonar el repositorio
Ejecuta el siguiente comando en tu terminal:
```bash
git clone https://github.com/SirAxLord/Chatbot.git
cd Chatbot
```

### 2️⃣ Construir y ejecutar con Docker Compose
Para construir la imagen y ejecutar todos los servicios en segundo plano:
```bash
docker-compose up -d --build
```

### 3️⃣ Entrenar el modelo de Rasa
Para entrenar el modelo del chatbot:
```bash
docker-compose run --rm rasa rasa train
```

### 4️⃣ Reiniciar el servidor de acciones
Después de entrenar o hacer cambios en las acciones personalizadas:
```bash
docker-compose restart actions
```

### 5️⃣ Interactuar con el chatbot
Para usar el chatbot desde la terminal:
```bash
docker-compose run --rm rasa rasa shell
```

## 🌐 Interfaz Web

El proyecto incluye una **interfaz web** para interactuar con el chatbot:

1. Asegúrate de que el servidor de Rasa esté en ejecución.
2. Abre el archivo `index.html` desde tu explorador de archivos.
3. Comenzará a funcionar automáticamente mientras el servicio de Rasa esté activo.

> **Nota:** La interfaz web solo funciona cuando los servicios de Rasa están en ejecución.

## 🛑 Detener los servicios

Para detener todos los contenedores en ejecución:
```bash
docker-compose down
```

## 📌 Notas adicionales

- Asegúrate de tener **Docker** y **Docker Compose** instalados en tu computadora.
- Si tienes problemas con permisos, prueba ejecutando los comandos con `sudo` en Linux.
- Para ver los logs de los servicios en ejecución:
  ```bash
  docker-compose logs -f
  ```
- Para reconstruir completamente las imágenes:
  ```bash
  docker-compose build --no-cache
  ```

---

¡Listo! 🚀 Ahora puedes usar el chatbot tanto desde la **terminal** como desde la **interfaz web**. 😃
