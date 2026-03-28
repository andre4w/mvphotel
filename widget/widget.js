(function () {
  "use strict";

  // ── Config ──────────────────────────────────────────────────────────────────
  var config = window.HotelAIConfig || {};
  var HOTEL_TOKEN = config.hotelToken;
  var BACKEND_URL = (function () {
    var scripts = document.getElementsByTagName("script");
    for (var i = 0; i < scripts.length; i++) {
      var src = scripts[i].src || "";
      if (src.indexOf("widget.js") !== -1) {
        return src.replace(/\/widget\.js.*$/, "");
      }
    }
    return "http://localhost:8000";
  })();

  if (!HOTEL_TOKEN) {
    console.warn("[HotelAI] Missing hotelToken in HotelAIConfig");
    return;
  }

  // ── Session ID ──────────────────────────────────────────────────────────────
  var SESSION_KEY = "hotelai_session_" + HOTEL_TOKEN;
  var sessionId = sessionStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId =
      "sess_" +
      Math.random().toString(36).substr(2, 9) +
      "_" +
      Date.now().toString(36);
    sessionStorage.setItem(SESSION_KEY, sessionId);
  }

  // ── Language detection ──────────────────────────────────────────────────────
  var userLang =
    (navigator.language || navigator.userLanguage || "en")
      .split("-")[0]
      .toLowerCase();

  var LABELS = {
    it: {
      placeholder: "Scrivi un messaggio…",
      greeting:
        "Ciao! Sono l'assistente virtuale dell'hotel. Come posso aiutarti?",
      error: "Si è verificato un errore. Riprova tra poco.",
      title: "Assistente Hotel",
      close: "Chiudi",
    },
    en: {
      placeholder: "Type a message…",
      greeting: "Hello! I'm the hotel virtual assistant. How can I help you?",
      error: "Something went wrong. Please try again.",
      title: "Hotel Assistant",
      close: "Close",
    },
    de: {
      placeholder: "Nachricht schreiben…",
      greeting:
        "Hallo! Ich bin der virtuelle Assistent des Hotels. Wie kann ich Ihnen helfen?",
      error: "Ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut.",
      title: "Hotel Assistent",
      close: "Schließen",
    },
    fr: {
      placeholder: "Écrivez un message…",
      greeting:
        "Bonjour ! Je suis l'assistant virtuel de l'hôtel. Comment puis-je vous aider?",
      error: "Une erreur s'est produite. Veuillez réessayer.",
      title: "Assistant Hôtel",
      close: "Fermer",
    },
    es: {
      placeholder: "Escribe un mensaje…",
      greeting:
        "¡Hola! Soy el asistente virtual del hotel. ¿En qué puedo ayudarte?",
      error: "Algo salió mal. Por favor, inténtalo de nuevo.",
      title: "Asistente del Hotel",
      close: "Cerrar",
    },
  };

  var L = LABELS[userLang] || LABELS["en"];

  // ── Styles ──────────────────────────────────────────────────────────────────
  var css = `
    #hotelai-widget * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    #hotelai-bubble {
      position: fixed; bottom: 24px; right: 24px; z-index: 99999;
      width: 56px; height: 56px; border-radius: 50%;
      background: linear-gradient(135deg, #1a3c5e 0%, #2d6a9f 100%);
      box-shadow: 0 4px 20px rgba(0,0,0,0.25);
      cursor: pointer; border: none; outline: none;
      display: flex; align-items: center; justify-content: center;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    #hotelai-bubble:hover { transform: scale(1.07); box-shadow: 0 6px 26px rgba(0,0,0,0.3); }
    #hotelai-bubble svg { width: 26px; height: 26px; fill: white; }
    #hotelai-bubble .hotelai-badge {
      position: absolute; top: -4px; right: -4px;
      background: #e74c3c; color: white; border-radius: 50%;
      width: 18px; height: 18px; font-size: 11px; font-weight: bold;
      display: flex; align-items: center; justify-content: center;
      border: 2px solid white;
    }
    #hotelai-panel {
      position: fixed; bottom: 92px; right: 24px; z-index: 99998;
      width: 360px; max-width: calc(100vw - 48px);
      height: 520px; max-height: calc(100vh - 120px);
      background: #fff; border-radius: 16px;
      box-shadow: 0 8px 40px rgba(0,0,0,0.18);
      display: flex; flex-direction: column; overflow: hidden;
      transform: scale(0.9) translateY(20px); opacity: 0;
      transform-origin: bottom right;
      transition: transform 0.25s ease, opacity 0.25s ease;
      pointer-events: none;
    }
    #hotelai-panel.open { transform: scale(1) translateY(0); opacity: 1; pointer-events: all; }
    #hotelai-header {
      background: linear-gradient(135deg, #1a3c5e 0%, #2d6a9f 100%);
      color: white; padding: 16px 20px;
      display: flex; align-items: center; justify-content: space-between;
      flex-shrink: 0;
    }
    #hotelai-header .hotelai-title-wrap { display: flex; align-items: center; gap: 10px; }
    #hotelai-header .hotelai-avatar {
      width: 36px; height: 36px; border-radius: 50%;
      background: rgba(255,255,255,0.2);
      display: flex; align-items: center; justify-content: center;
    }
    #hotelai-header .hotelai-avatar svg { width: 20px; height: 20px; fill: white; }
    #hotelai-header h3 { font-size: 15px; font-weight: 600; }
    #hotelai-header p { font-size: 11px; opacity: 0.8; margin-top: 1px; }
    #hotelai-close {
      background: none; border: none; cursor: pointer;
      color: white; opacity: 0.8; padding: 4px;
      border-radius: 6px; transition: opacity 0.2s;
    }
    #hotelai-close:hover { opacity: 1; }
    #hotelai-close svg { width: 18px; height: 18px; fill: white; display: block; }
    #hotelai-messages {
      flex: 1; overflow-y: auto; padding: 16px;
      display: flex; flex-direction: column; gap: 12px;
      background: #f8f9fa;
    }
    #hotelai-messages::-webkit-scrollbar { width: 4px; }
    #hotelai-messages::-webkit-scrollbar-thumb { background: #ccc; border-radius: 4px; }
    .hotelai-msg { display: flex; gap: 8px; max-width: 90%; }
    .hotelai-msg.user { align-self: flex-end; flex-direction: row-reverse; }
    .hotelai-msg.bot { align-self: flex-start; }
    .hotelai-msg .hotelai-bubble-msg {
      padding: 10px 14px; border-radius: 16px;
      font-size: 13.5px; line-height: 1.5; word-break: break-word;
    }
    .hotelai-msg.user .hotelai-bubble-msg {
      background: linear-gradient(135deg, #1a3c5e, #2d6a9f);
      color: white; border-bottom-right-radius: 4px;
    }
    .hotelai-msg.bot .hotelai-bubble-msg {
      background: white; color: #1a1a2e;
      border-bottom-left-radius: 4px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }
    .hotelai-msg .hotelai-avatar-small {
      width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0;
      background: linear-gradient(135deg, #1a3c5e, #2d6a9f);
      display: flex; align-items: center; justify-content: center; margin-top: 2px;
    }
    .hotelai-msg .hotelai-avatar-small svg { width: 14px; height: 14px; fill: white; }
    .hotelai-typing { display: flex; gap: 4px; padding: 12px 14px; }
    .hotelai-typing span {
      width: 7px; height: 7px; border-radius: 50%; background: #aaa;
      animation: hotelai-bounce 1.2s infinite;
    }
    .hotelai-typing span:nth-child(2) { animation-delay: 0.2s; }
    .hotelai-typing span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes hotelai-bounce {
      0%, 60%, 100% { transform: translateY(0); }
      30% { transform: translateY(-6px); }
    }
    #hotelai-input-area {
      padding: 12px 16px; background: white;
      border-top: 1px solid #eee; display: flex; gap: 8px; flex-shrink: 0;
    }
    #hotelai-input {
      flex: 1; border: 1.5px solid #e0e0e0; border-radius: 22px;
      padding: 9px 16px; font-size: 13.5px; outline: none;
      transition: border-color 0.2s; resize: none; max-height: 80px;
      font-family: inherit; line-height: 1.4;
    }
    #hotelai-input:focus { border-color: #2d6a9f; }
    #hotelai-send {
      width: 38px; height: 38px; border-radius: 50%; border: none;
      background: linear-gradient(135deg, #1a3c5e, #2d6a9f);
      cursor: pointer; display: flex; align-items: center; justify-content: center;
      flex-shrink: 0; transition: opacity 0.2s; align-self: flex-end;
    }
    #hotelai-send:hover { opacity: 0.85; }
    #hotelai-send svg { width: 16px; height: 16px; fill: white; }
    #hotelai-send:disabled { opacity: 0.4; cursor: not-allowed; }
    @media (max-width: 400px) {
      #hotelai-panel { width: calc(100vw - 32px); right: 16px; bottom: 80px; }
      #hotelai-bubble { bottom: 16px; right: 16px; }
    }
  `;

  // ── SVG icons ────────────────────────────────────────────────────────────────
  var ICON_CHAT =
    '<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/></svg>';
  var ICON_CLOSE =
    '<svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>';
  var ICON_SEND =
    '<svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>';
  var ICON_BOT =
    '<svg viewBox="0 0 24 24"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7H3a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2M7 14v2a1 1 0 0 0 1 1h1v3h6v-3h1a1 1 0 0 0 1-1v-2H7m2-2.5a1 1 0 1 0 0 2 1 1 0 0 0 0-2m6 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2z"/></svg>';

  // ── Build DOM ────────────────────────────────────────────────────────────────
  var styleEl = document.createElement("style");
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  var wrapper = document.createElement("div");
  wrapper.id = "hotelai-widget";

  // Bubble button
  var bubble = document.createElement("button");
  bubble.id = "hotelai-bubble";
  bubble.setAttribute("aria-label", L.title);
  bubble.innerHTML = ICON_CHAT;

  var badge = document.createElement("span");
  badge.className = "hotelai-badge";
  badge.style.display = "none";
  badge.textContent = "!";
  bubble.appendChild(badge);

  // Panel
  var panel = document.createElement("div");
  panel.id = "hotelai-panel";
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-label", L.title);

  panel.innerHTML = `
    <div id="hotelai-header">
      <div class="hotelai-title-wrap">
        <div class="hotelai-avatar">${ICON_BOT}</div>
        <div>
          <h3>${L.title}</h3>
          <p>Online</p>
        </div>
      </div>
      <button id="hotelai-close" aria-label="${L.close}">${ICON_CLOSE}</button>
    </div>
    <div id="hotelai-messages" role="log" aria-live="polite"></div>
    <div id="hotelai-input-area">
      <textarea id="hotelai-input" rows="1" placeholder="${L.placeholder}" maxlength="1000"></textarea>
      <button id="hotelai-send" aria-label="Send">${ICON_SEND}</button>
    </div>
  `;

  wrapper.appendChild(bubble);
  wrapper.appendChild(panel);
  document.body.appendChild(wrapper);

  // ── State ────────────────────────────────────────────────────────────────────
  var isOpen = false;
  var isLoading = false;
  var unreadCount = 0;
  var greetingShown = false;

  var messagesEl = document.getElementById("hotelai-messages");
  var inputEl = document.getElementById("hotelai-input");
  var sendBtn = document.getElementById("hotelai-send");

  // ── Helpers ──────────────────────────────────────────────────────────────────
  function togglePanel() {
    isOpen = !isOpen;
    panel.classList.toggle("open", isOpen);
    bubble.innerHTML = (isOpen ? ICON_CLOSE : ICON_CHAT) + badge.outerHTML;
    // Re-grab badge reference after innerHTML update
    badge = bubble.querySelector(".hotelai-badge");

    if (isOpen) {
      unreadCount = 0;
      badge.style.display = "none";
      if (!greetingShown) {
        greetingShown = true;
        addMessage("bot", L.greeting);
      }
      setTimeout(function () { inputEl.focus(); }, 250);
    }
  }

  function addMessage(role, text) {
    var msgEl = document.createElement("div");
    msgEl.className = "hotelai-msg " + role;

    var bubbleMsg = document.createElement("div");
    bubbleMsg.className = "hotelai-bubble-msg";
    // Allow basic line breaks
    bubbleMsg.innerHTML = text.replace(/\n/g, "<br>");

    if (role === "bot") {
      var avatarEl = document.createElement("div");
      avatarEl.className = "hotelai-avatar-small";
      avatarEl.innerHTML = ICON_BOT;
      msgEl.appendChild(avatarEl);
    }

    msgEl.appendChild(bubbleMsg);
    messagesEl.appendChild(msgEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return msgEl;
  }

  function showTyping() {
    var typingEl = document.createElement("div");
    typingEl.className = "hotelai-msg bot";
    typingEl.id = "hotelai-typing";
    typingEl.innerHTML =
      '<div class="hotelai-avatar-small">' +
      ICON_BOT +
      '</div><div class="hotelai-bubble-msg"><div class="hotelai-typing"><span></span><span></span><span></span></div></div>';
    messagesEl.appendChild(typingEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function removeTyping() {
    var el = document.getElementById("hotelai-typing");
    if (el) el.remove();
  }

  function setLoading(val) {
    isLoading = val;
    sendBtn.disabled = val;
    inputEl.disabled = val;
  }

  // ── Send message ─────────────────────────────────────────────────────────────
  function sendMessage() {
    var text = inputEl.value.trim();
    if (!text || isLoading) return;

    inputEl.value = "";
    inputEl.style.height = "auto";
    addMessage("user", text);
    setLoading(true);
    showTyping();

    var payload = JSON.stringify({
      hotel_token: HOTEL_TOKEN,
      session_id: sessionId,
      message: text,
      language: userLang,
    });

    var xhr = new XMLHttpRequest();
    xhr.open("POST", BACKEND_URL + "/chat", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = function () {
      if (xhr.readyState !== 4) return;
      removeTyping();
      setLoading(false);

      if (xhr.status === 200) {
        try {
          var data = JSON.parse(xhr.responseText);
          addMessage("bot", data.response);

          // Show badge if panel is closed
          if (!isOpen) {
            unreadCount++;
            badge.style.display = "flex";
            badge.textContent = unreadCount > 9 ? "9+" : String(unreadCount);
          }
        } catch (e) {
          addMessage("bot", L.error);
        }
      } else {
        addMessage("bot", L.error);
      }
    };
    xhr.onerror = function () {
      removeTyping();
      setLoading(false);
      addMessage("bot", L.error);
    };
    xhr.send(payload);
  }

  // ── Event listeners ──────────────────────────────────────────────────────────
  bubble.addEventListener("click", togglePanel);
  document.getElementById("hotelai-close").addEventListener("click", togglePanel);
  sendBtn.addEventListener("click", sendMessage);

  inputEl.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Auto-resize textarea
  inputEl.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = Math.min(this.scrollHeight, 80) + "px";
  });

  // Close panel when clicking outside
  document.addEventListener("click", function (e) {
    if (isOpen && !wrapper.contains(e.target)) {
      togglePanel();
    }
  });
})();
