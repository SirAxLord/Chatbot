# Chatbot Rasa con Docker

Este proyecto es un chatbot desarrollado con **Rasa** y ejecutado dentro de un contenedor **Docker**.

## 🚀 Instrucciones de Instalación

### 1️⃣ Clonar el repositorio
Ejecuta el siguiente comando en tu terminal:
```bash
git clone https://github.com/SirAxLord/Chatbot.git
cd chatbot-rasa
```

### 2️⃣ Construir la imagen de Docker
Ejecuta el siguiente comando para construir la imagen del chatbot:
```bash
docker build -t chatbot-rasa .
```
Esto creará una imagen de Docker llamada `chatbot-rasa`.

### 3️⃣ Ejecutar el contenedor
Para correr el chatbot, usa:
```bash
docker run -p 5005:5005 chatbot-rasa
```
Si todo está bien, verás un mensaje indicando que el servidor está corriendo en `http://0.0.0.0:5005`.

### 4️⃣ Probar el chatbot
Abre un navegador y ve a:
```
http://localhost:5005
```
También puedes probarlo desde la terminal con:
```bash
curl http://localhost:5005/version
```

## 🛑 Detener el contenedor
Para detener el contenedor en ejecución, presiona `CTRL + C` en la terminal o usa:
```bash
docker ps   # Para ver el ID del contenedor
docker stop <ID_DEL_CONTENEDOR>
```

## 📌 Notas
- Asegúrate de tener **Docker instalado** en tu computadora.
- Si tienes problemas con permisos, prueba ejecutando los comandos con `sudo` en Linux.
- Si necesitas reconstruir la imagen, usa `docker build --no-cache -t chatbot-rasa .` para evitar problemas de caché.

¡Listo! 🚀 Ahora puedes usar el chatbot en tu máquina. 😃

