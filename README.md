# GenAI & Agentic AI Studio

A modular Django application structured into **4 independent modes**, each with completely isolated backend logic.

---

## 🧭 The 4 Modular Modes

| Mode | URL | Purpose | Backend File | Security |
| :--- | :--- | :--- | :--- | :--- |
| **1. 💬 Standard Chat** | `/chat/` | Online Gemini Chat (pure conversational) | `backends/standard_chat.py` | Open |
| **2. 🦙 Offline Model** | `/chat/offline/` | Local Ollama execution (zero internet) | `backends/offline_chat.py` | Open (Local) |
| **3. 🛠️ Limited Agent** | `/chat/limited-agent/` | Safe pre-defined tools (Clock, Math, Weather, Brightness) | `backends/limited_agent.py` | Sandboxed tools |
| **4. 💻 Universal Agent** | `/chat/universal-agent/` | Full OS PowerShell control with Confirmation & Password | `backends/universal_agent.py` | **🔒 Password Protected** |

---

## 🔒 Universal Agent Security & Password

Because the Universal Agent can execute PowerShell commands on your laptop, it has a dual-layer security guardrail:
1. **Interactive Confirmation:** You must explicitly click **Approve & Run** on every proposed command.
2. **Password Authorization:** You must provide the authorization password (configured via `UNIVERSAL_AGENT_PASSWORD` in `.env`, default: `admin123`).

If the wrong password is provided, access is strictly denied with HTTP 403 Forbidden.

---

## 📁 Architecture Overview

```
genai_app/chat/
├── backends/
│   ├── standard_chat.py       # Online Gemini logic
│   ├── offline_chat.py        # Local Ollama logic
│   ├── limited_agent.py       # Specific safe tools & agent loop
│   └── universal_agent.py     # PowerShell agent + password auth
├── templates/chat/
│   ├── standard.html          # Standard chat UI
│   ├── offline.html           # Offline model UI with model selector
│   ├── limited_agent.html     # Limited tools UI with tool tray
│   └── universal_agent.html   # Universal agent UI with password approval card
├── views.py                   # Clean routes delegating to backends
└── urls.py                    # URL mappings
```

---

## 🏃 Running the Application

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Start the server
cd genai_app
python manage.py runserver 8080
```

Open:
- **[http://localhost:8080/chat/](http://localhost:8080/chat/)** — Standard Chat
- **[http://localhost:8080/chat/offline/](http://localhost:8080/chat/offline/)** — Offline Model
- **[http://localhost:8080/chat/limited-agent/](http://localhost:8080/chat/limited-agent/)** — Limited Tools Agent
- **[http://localhost:8080/chat/universal-agent/](http://localhost:8080/chat/universal-agent/)** — Universal Agent

---

## 🧪 Run Tests

```powershell
python manage.py test
```
*(All 12 tests pass in ~0.02s).*
