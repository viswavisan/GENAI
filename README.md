# GenAI & Agentic AI Studio

A clean, modular Django workspace clearly separated into **3 functional groups**, each with isolated backend modules that can be integrated or removed independently.

---

## 🧭 The 3 Functional Groups

### 1. 💬 GenAI Chat (Pure Conversational LLM - No Tools)
- **🌐 Online Chat (`/chat/`):** Powered by Google Gemini (`gemini-3-flash-preview`). Open chat for creative writing, explanations, and code.
- **🦙 Offline Chat (`/chat/offline/`):** Powered by local Ollama (`llama3.2` or any local model). Runs 100% offline without internet.
- **Backend File:** `chat/backends/genai_chat.py`

### 2. ⚡ Agentic AI Online (Cloud Gemini with Autonomous Function Calling)
- **🛠️ Limited Tools (`/chat/agent/limited/`):** Sandboxed, predefined safe tools (Real-time Clock, Calculator, Weather Forecast, Screen Brightness, String Reversal).
- **💻 Universal PowerShell Agent (`/chat/agent/universal/`):** Full OS capability via PowerShell. Guarded by **Human-in-the-Loop Confirmation** and **Authorization Password**.
- **Backend File:** `chat/backends/agentic_online.py`

### 3. 🛡️ Agentic AI Offline (Local Tool-Calling Agent - Zero Internet)
- **🛡️ Local Autonomous Agent (`/chat/agent/offline/`):** Uses local Ollama `/api/chat` function calling to reason, select local tools (Clock, Calculator, Laptop Brightness, String Reversal), execute them locally, and synthesize final answers.
- **Backend File:** `chat/backends/agentic_offline.py`

---

## 🔒 Universal Agent Security Guardrails

Because the Universal Agent can run PowerShell commands on the host machine, it includes a two-stage security guardrail:
1. **Interactive Confirmation:** The agent proposes the command and pauses; you must click **Authenticate & Run**.
2. **Password Authorization:** Requires the authorization password configured in `.env` via `UNIVERSAL_AGENT_PASSWORD` (default: `admin123`).
3. Invalid passwords immediately return **HTTP 403 Forbidden**.

---

## 📁 Clean Repository Layout

The project lives directly at the root (no redundant nested folders):

```
GENAI/
├── .env                       # Environment secrets (GEMINI_API_KEY, UNIVERSAL_AGENT_PASSWORD)
├── .env.example               # Template for environment configuration
├── .gitignore                 # Standard Python & Django ignore rules
├── requirements.txt           # Locked dependency list
├── manage.py                  # Django management entry point
├── db.sqlite3                 # SQLite database
├── static/                    # Static assets
├── config/                    # Django project settings & root URLs
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── chat/                      # Main GenAI & Agentic AI application
    ├── backends/              # 100% isolated backend logic modules
    │   ├── genai_chat.py      # Group 1: Online & Offline Conversational LLM
    │   ├── agentic_online.py  # Group 2: Limited & Universal Cloud Agents
    │   └── agentic_offline.py # Group 3: Offline Local Tool Calling Agent
    ├── templates/chat/        # Rich dark-mode UI templates
    │   ├── genai_online.html
    │   ├── genai_offline.html
    │   ├── agent_online_limited.html
    │   ├── agent_online_universal.html
    │   └── agent_offline.html
    ├── views.py               # Clean endpoint views delegating to backends
    ├── urls.py                # Route definitions
    └── tests.py               # Comprehensive 16-test suite covering all 3 groups
```

---

## 🏃 Quickstart

### 1. Configure Environment
Ensure your `.env` contains:
```env
GEMINI_API_KEY=your_gemini_api_key_here
UNIVERSAL_AGENT_PASSWORD=admin123
OLLAMA_BASE_URL=http://localhost:11434
```

### 2. Run the Server
From the root directory:
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run server directly from root
python manage.py runserver 8080
```

### 3. Open in Browser
- **GenAI Online Chat:** [http://localhost:8080/chat/](http://localhost:8080/chat/)
- **GenAI Offline Chat:** [http://localhost:8080/chat/offline/](http://localhost:8080/chat/offline/)
- **Agentic Online (Limited):** [http://localhost:8080/chat/agent/limited/](http://localhost:8080/chat/agent/limited/)
- **Agentic Online (Universal):** [http://localhost:8080/chat/agent/universal/](http://localhost:8080/chat/agent/universal/)
- **Agentic Offline (Local Agent):** [http://localhost:8080/chat/agent/offline/](http://localhost:8080/chat/agent/offline/)

*(Backward-compatible URLs like `/chat/limited-agent/` and `/chat/universal-agent/` continue to work seamlessly).*
