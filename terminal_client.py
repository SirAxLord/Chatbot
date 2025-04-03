import requests
import json

def send_message(message, sender="user"):
    """Envía un mensaje al servidor Rasa y devuelve la respuesta."""
    url = "http://localhost:5005/webhooks/rest/webhook"
    payload = {
        "sender": sender,
        "message": message
    }
    response = requests.post(url, json=payload)
    return response.json()

def main():
    print("Bienvenido al Asistente Académico. Escribe 'salir' para terminar.")
    
    sender_id = "user_terminal"  # Identificador único para esta sesión
    
    while True:
        user_message = input("\nTú: ")
        
        if user_message.lower() == "salir":
            print("¡Hasta pronto!")
            break
        
        # Enviar mensaje a Rasa
        responses = send_message(user_message, sender_id)
        
        # Mostrar respuestas
        if responses:
            for response in responses:
                print(f"\nBot: {response.get('text', '')}")
        else:
            print("\nBot: Lo siento, no pude procesar tu mensaje.")

if __name__ == "__main__":
    main()