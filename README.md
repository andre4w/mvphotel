# Hotel AI Platform — MVP

Piattaforma AI per hotel composta da:
- **Widget chat** embeddabile su qualsiasi sito web (JavaScript vanilla)
- **Dashboard backend** per la gestione dell'hotel (HTML/CSS/JS + FastAPI)

---

## Architettura

```
mvphotel/
├── backend/          # FastAPI + SQLite
│   ├── main.py       # App principale, tutti gli endpoint
│   ├── database.py   # Setup SQLite e tabelle
│   ├── models.py     # Schemi Pydantic
│   ├── auth.py       # JWT authentication
│   ├── scraper.py    # Web scraper (httpx + BeautifulSoup4)
│   ├── ai.py         # Integrazione Claude (Anthropic)
│   ├── requirements.txt
│   └── .env.example
├── frontend/         # Dashboard hotel (HTML/CSS/JS vanilla)
│   ├── index.html    # Login / Registrazione
│   ├── dashboard.html# Dashboard principale
│   └── style.css
├── widget/
│   └── widget.js     # Widget chat embeddabile
└── README.md
```

---

## Prerequisiti

- Python 3.10+
- Un API key di Anthropic (Claude)

---

## Setup e avvio

### 1. Clona il repository

```bash
git clone <repo-url>
cd mvphotel
```

### 2. Configura le variabili d'ambiente

```bash
cd backend
cp .env.example .env
```

Modifica il file `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-la-tua-chiave-qui
SECRET_KEY=una-stringa-segreta-casuale-lunga
DATABASE_URL=./hotel_platform.db
BACKEND_URL=http://localhost:8000
```

> **Importante:** `BACKEND_URL` deve corrispondere all'URL pubblico del backend.
> In locale usa `http://localhost:8000`. In produzione usa l'URL del tuo server.

### 3. Installa le dipendenze Python

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Su Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Avvia il backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Il backend sarà disponibile su `http://localhost:8000`.
Documentazione API interattiva: `http://localhost:8000/docs`

### 5. Apri la dashboard

Apri il file `frontend/index.html` nel browser (doppio clic, oppure con un server locale):

```bash
# Opzione A: apri direttamente nel browser
open frontend/index.html

# Opzione B: server locale Python (consigliato)
cd frontend
python -m http.server 3000
# poi vai su http://localhost:3000
```

---

## Utilizzo

### Registrazione e configurazione

1. Vai su `http://localhost:3000` (o apri `frontend/index.html`)
2. Clicca su **Registrati** e crea un account per il tuo hotel
3. Vai su **Impostazioni** e inserisci:
   - Nome dell'hotel
   - Numero di telefono
   - URL del sito web
4. Vai su **Scansione sito** e clicca **Avvia scansione**
   - Il sistema visita automaticamente le pagine del tuo sito
   - Estrae testo utile (camere, servizi, prezzi, contatti, policy, ecc.)
   - Lo stato si aggiorna in tempo reale ogni 3 secondi

### Installazione del widget

1. Vai su **Installa widget**
2. Copia lo snippet HTML
3. Incollalo nel tuo sito web **prima della chiusura del tag `</body>`**:

```html
<!-- Hotel AI Chat Widget -->
<script>
  window.HotelAIConfig = { hotelToken: "il-tuo-token-univoco" };
</script>
<script src="http://localhost:8000/widget.js" async></script>
<!-- End Hotel AI Chat Widget -->
```

### Gestione notifiche

- Quando la chat non riesce a rispondere a una domanda, viene salvata nella sezione **Notifiche**
- Puoi aggiungere manualmente la risposta mancante
- La risposta viene inclusa nel contesto dell'AI per le richieste future

---

## API Endpoints

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| POST | `/auth/register` | Registra un nuovo hotel |
| POST | `/auth/login` | Login, ritorna JWT |
| GET | `/hotel/me` | Profilo hotel autenticato |
| PUT | `/hotel/me` | Aggiorna profilo hotel |
| POST | `/hotel/scan` | Avvia scansione sito (background) |
| GET | `/hotel/scan/status` | Stato scansione + numero pagine |
| GET | `/hotel/snippet` | Snippet HTML da installare |
| GET | `/hotel/notifications` | Domande senza risposta |
| POST | `/hotel/notifications/{id}/answer` | Aggiungi risposta manuale |
| POST | `/chat` | Endpoint pubblico per il widget |
| GET | `/widget.js` | Serve il file JavaScript del widget |
| GET | `/health` | Health check |

---

## Come funziona la chat

1. Il widget JS viene caricato sul sito dell'hotel con il token univoco
2. Quando un ospite invia un messaggio, il widget chiama `POST /chat`
3. Il backend carica le pagine scansionate del sito come contesto
4. Include anche le risposte manuali aggiunte in dashboard
5. Passa tutto a Claude (Anthropic) che risponde nella lingua del visitatore
6. Se Claude non trova la risposta nel contesto, segnala `CANNOT_ANSWER`
7. Il backend salva la domanda nella tabella `unanswered_questions` e invia la notifica

---

## Note tecniche

- **Database:** SQLite (`hotel_platform.db`) nella cartella `backend/`
- **Auth:** JWT con scadenza 7 giorni
- **Scraping:** crawl BFS fino a 30 pagine, stesso dominio, delay 300ms tra richieste
- **AI:** Claude `claude-sonnet-4-6`, max 800 token di risposta, ultimi 10 messaggi come contesto
- **Widget:** Nessuna dipendenza esterna, JavaScript vanilla ES5-compatibile

---

## Variabili d'ambiente

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `ANTHROPIC_API_KEY` | API key Anthropic (Claude) | — (obbligatoria) |
| `SECRET_KEY` | Chiave JWT | `dev-secret-key-change-in-production` |
| `DATABASE_URL` | Path del database SQLite | `./hotel_platform.db` |
| `BACKEND_URL` | URL pubblico del backend | `http://localhost:8000` |
