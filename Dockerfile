# Usar la imagen oficial de Python
FROM python:3.10

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar los archivos del proyecto al contenedor
COPY . /app

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto de Rasa (5005)
EXPOSE 5005

# Comando para ejecutar el chatbot con Rasa
CMD ["rasa", "run", "--enable-api", "--cors", "*"]
