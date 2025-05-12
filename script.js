// script.js - Lógica de comunicación con Rasa y manejo de la interfaz, AÑADIENDO INDICADOR DE CARGA

document.addEventListener('DOMContentLoaded', () => {
    // Obtenemos referencias a los elementos HTML
    const chatBox = document.getElementById('chat-box');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');

    // --- Función para añadir un mensaje a la caja de chat (incluye formato de lista) ---
    function addMessage(sender, text) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', `${sender}-message`);

        let formattedHtml = '';

        // --- LÓGICA ESPECÍFICA PARA MENSAJES CON FORMATO DE LISTA ---
        // 1. Lógica para el mensaje del PLAN DE ESTUDIOS
        if (sender === 'bot' && text.startsWith('Plan de estudios de') && text.includes('Semestre')) {
            const semestreIndex = text.indexOf('Semestre');
            const header = text.substring(0, semestreIndex).trim();
            const semestrePart = text.substring(semestreIndex).trim();
            const colonIndexAfterSemestre = semestrePart.indexOf(':');
            if (colonIndexAfterSemestre !== -1) {
                const semestreHeader = semestrePart.substring(0, colonIndexAfterSemestre + 1).trim();
                const subjectsString = semestrePart.substring(colonIndexAfterSemestre + 1).trim();
                const subjectsList = subjectsString.split(',').map(item => item.trim()).filter(item => item.length > 0);
                formattedHtml = `${header}<br>${semestreHeader}<br>`;
                formattedHtml += '<ul>';
                subjectsList.forEach(subject => { if (subject) formattedHtml += `<li>${subject}</li>`; });
                formattedHtml += '</ul>';
            } else { formattedHtml = text.replace(/\n/g, '<br>'); }
        }
        // 2. Lógica para el mensaje de LISTA DE ÁREAS DE ÉNFASIS
        else if (sender === 'bot' && text.startsWith('Las áreas de énfasis en la carrera de')) {
             const lines = text.split('\n');
             const header = lines[0];
             const areasListLines = lines.slice(1);
             formattedHtml = `${header}<br>`;
             formattedHtml += '<ul>';
             areasListLines.forEach(areaLine => {
                 if (areaLine.trim().startsWith('- ')) { formattedHtml += `<li>${areaLine.trim().substring(2).trim()}</li>`; }
                 else if (areaLine.trim().length > 0) { formattedHtml += areaLine.trim() + '<br>'; }
             });
             formattedHtml += '</ul>';
        }
         // 3. Lógica para el mensaje de LISTA DE MATERIAS EN UN ÁREA
        else if (sender === 'bot' && text.startsWith('Las materias en el área de')) {
             const lines = text.split('\n');
             const header = lines[0];
             const subjectsLine = lines.slice(1).join(' ').trim();
             formattedHtml = `${header}<br>`;
             if (subjectsLine.startsWith('- ')) {
                 const subjectsString = subjectsLine.substring(2).trim();
                 const subjectsList = subjectsString.split(',').map(item => item.trim()).filter(item => item.length > 0);
                 formattedHtml += '<ul>';
                 subjectsList.forEach(subject => { if (subject) formattedHtml += `<li>${subject}</li>`; });
                 formattedHtml += '</ul>';
             } else if (subjectsLine.length > 0) { formattedHtml += subjectsLine.replace(/\n/g, '<br>'); }
             else { formattedHtml = header + '<br>No se encontraron materias listadas para este área.'; }
        }
        // --- LÓGICA PARA OTROS MENSAJES (EXISTENTE) ---
        else {
            formattedHtml = text.replace(/\n/g, '<br>');
        }
        // --- FIN LÓGICA CONDICIONAL ---

        messageElement.innerHTML = formattedHtml;
        chatBox.appendChild(messageElement);

        // Hacer scroll automático al final de la conversación
        setTimeout(() => {
             chatBox.scrollTop = chatBox.scrollHeight;
        }, 50);
    }

    // --- Función para crear y añadir el indicador de carga ---
    function showTypingIndicator() {
        const indicatorElement = document.createElement('div');
        // Usamos las clases de mensaje y bot-message para que herede estilos básicos
        indicatorElement.classList.add('message', 'bot-message', 'typing-indicator');

        // Añadimos los elementos span para los puntitos dentro del div
        indicatorElement.innerHTML = '<span></span><span></span><span></span>';

        chatBox.appendChild(indicatorElement);
        // Hacemos scroll para asegurar que el indicador sea visible
        chatBox.scrollTop = chatBox.scrollHeight;

        // Retornamos el elemento creado para poder referenciarlo y eliminarlo después
        return indicatorElement;
    }

    // --- Función para eliminar el indicador de carga ---
    function hideTypingIndicator(indicatorElement) {
        // Verificamos que el elemento exista y sea parte del DOM antes de intentar eliminarlo
        if (indicatorElement && chatBox.contains(indicatorElement)) {
             chatBox.removeChild(indicatorElement);
        }
    }

    // --- Función para enviar mensaje a Rasa y get response - MODIFICADA CON INDICADOR DE CARGA Y TIEMPO MÍNIMO ---
    async function sendMessageToRasa(message) {
        const rasaEndpoint = 'http://localhost:5005/webhooks/rest/webhook';
        const senderId = 'web-user-123';
        // Tiempo mínimo que el indicador debe mostrarse (en milisegundos). Ej: 1500ms = 1.5 segundos.
        const minDisplayTime = 1500; // Puedes ajustar este valor (ej. 2000 para 2 segundos)

        // 1. Mostrar el indicador de carga inmediatamente después de que el usuario envía su mensaje
        const indicator = showTypingIndicator();

        // 2. Registrar el tiempo de inicio de la espera
        const startTime = Date.now();

        try {
            // 3. Enviar la petición fetch a Rasa (esta es la promesa que espera la respuesta del bot)
            const fetchPromise = fetch(rasaEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ sender: senderId, message: message })
            });

            // 4. Crear una promesa que se resolverá después del tiempo mínimo de visualización del indicador
            const timerPromise = new Promise(resolve => {
                setTimeout(resolve, minDisplayTime);
            });

            // 5. Esperar a que AMBAS promesas se completen: la de fetch (respuesta de Rasa) Y la del timer (tiempo mínimo)
            // Esto asegura que el indicador se muestre por al menos minDisplayTime, sin importar qué tan rápido responda Rasa.
            const [response] = await Promise.all([fetchPromise, timerPromise]);

            // 6. Una vez que ambas promesas se han resuelto, ocultar el indicador de carga
            hideTypingIndicator(indicator);

            // 7. Procesar la respuesta del fetch (igual que antes)
            if (!response.ok) {
                const errorBody = await response.text();
                 console.error(`Error HTTP! estado: ${response.status}`, errorBody);
                throw new Error(`Error HTTP! estado: ${response.status}`);
            }

            const messages = await response.json();

            if (messages.length === 0) {
                console.log("DEBUG: Rasa no devolvió mensajes.");
                // Opcional: Mostrar un mensaje genérico si Rasa no responde nada
                // addMessage('bot', 'No tengo respuesta para eso en este momento.');
            } else {
                 messages.forEach(msg => {
                    if (msg.text) {
                        addMessage('bot', msg.text); // addMessage ya maneja el formato de listas y saltos de línea
                    }
                    // Manejar otros tipos de mensajes (botones, imágenes, etc.) si es necesario aquí
                });
            }

        } catch (error) {
            console.error('Error al enviar mensaje a Rasa:', error);
            // Asegurarnos de ocultar el indicador incluso si ocurre un error
            hideTypingIndicator(indicator);
            addMessage('bot', 'Lo siento, hubo un error al conectar con el chatbot. Por favor, verifica que esté corriendo y la URL sea correcta.');
        }
    }

    // --- Event Listener para el botón Enviar ---
    sendButton.addEventListener('click', () => {
        const message = userInput.value.trim();
        if (message) {
            addMessage('user', message); // Añade el mensaje del usuario
            userInput.value = ''; // Limpia el input
            sendMessageToRasa(message); // Envía el mensaje a Rasa y maneja la respuesta con indicador
        }
    });

    // --- Event Listener para la tecla Enter en el input ---
    userInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault(); // Evita la acción por defecto del formulario
            sendButton.click(); // Simula el clic en el botón
        }
    });

    // --- Mensaje inicial al cargar la página ---
     addMessage('bot', 'Hola! Soy el asistente académico. ¿En qué puedo ayudarte?'); // Mensaje directo de bienvenida
});