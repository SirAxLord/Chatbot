// ID estable para mantener el historial (Redis/Tracker)
const KEY = "sender_id";
const sender =
	localStorage.getItem(KEY) ||
	crypto.randomUUID?.() ||
	"web-" + Math.random().toString(36).slice(2);
localStorage.setItem(KEY, sender);

const log = document.getElementById("log");
const form = document.getElementById("form");
const input = document.getElementById("msg");
const statusEl = document.getElementById("status");
const tpl = document.getElementById("tpl-msg");

// util: pintar mensajes
function push(text, who = "bot") {
	const node = tpl.content.firstElementChild.cloneNode(true);
	node.classList.add(who);
	node.querySelector(".bubble").textContent = text;
	log.appendChild(node);
	log.scrollTop = log.scrollHeight;
}

// ping rápido a /rasa/status para mostrar badge
async function ping() {
	try {
		const r = await fetch("/rasa/status");
		statusEl.textContent = r.ok ? "Listo" : "Sin modelo";
		statusEl.style.background = r.ok
			? "rgba(34,197,94,.15)"
			: "rgba(245,158,11,.15)";
	} catch {
		statusEl.textContent = "Sin conexión";
		statusEl.style.background = "rgba(245,158,11,.15)";
	}
}
ping();

// enviar al webhook REST estándar de Rasa
async function send(text) {
	// Deshabilita UI
	input.disabled = true;
	document.getElementById("send").disabled = true;

	try {
		// Endpoint oficial: /webhooks/rest/webhook (docs)
		// Body esperado: { sender, message }
		const res = await fetch("/rasa/webhooks/rest/webhook", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ sender, message: text }),
		});

		const ct = res.headers.get("content-type") || "";
		if (!res.ok || !ct.includes("application/json")) {
			const errText = await res.text();
			throw new Error(
				`HTTP ${res.status} ${res.statusText} — ${errText.slice(0, 180)}`
			);
		}

		const data = await res.json();

		if (Array.isArray(data) && data.length) {
			for (const m of data) {
				const text = m.text ?? (m.image ? "[imagen]" : JSON.stringify(m));
				push(text, "bot");
			}
		} else {
			push("No recibí respuesta del servidor.", "bot");
		}
	} catch (err) {
		push("Error de red: " + (err?.message || err), "bot");
	} finally {
		input.disabled = false;
		document.getElementById("send").disabled = false;
		input.focus();
	}
}

// UI
form.addEventListener("submit", (e) => {
	e.preventDefault();
	const text = input.value.trim();
	if (!text) return;
	push(text, "me");
	input.value = "";
	send(text);
});

// Mensaje de bienvenida
push("¡Hola! Soy tu asistente académico. ¿En qué te ayudo hoy?", "bot");
