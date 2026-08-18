# AI-Powered RAG Study Companion

A modular, production-ready full-stack **RAG (Retrieval-Augmented Generation) Study Companion** designed to help students ingest study PDFs, scanned material, and YouTube educational videos, ask questions grounded strictly in their sources, and interact with automated study tools (Quizzes, Flashcards, Summaries) guided by an agentic intent router.

---

## Development Progress

```text
Phase 0 — Foundation       ✅
Phase 1 — Basic RAG        ✅
Phase 2 — OCR Ingestion    ✅
Phase 3 — YouTube Ingest   ✅
Phase 4 — Study Tools      ✅
Phase 5 — Agent Router     ✅
```

---

## Tech Stack & Architecture

- **Backend**: Python 3.14+, Flask
- **PDF Processing**: PyMuPDF (fitz)
- **OCR Engine**: PyTesseract / PIL
- **Embeddings**: `sentence-transformers` (`all-MiniLM-L6-v2`)
- **Vector Database**: Persistent ChromaDB
- **LLM Engine**: Groq API (`llama-3.3-70b-versatile`)
- **YouTube API**: `youtube-transcript-api`
- **Frontend**: Clean Academic UI (HTML5, CSS3 with modern CSS custom properties, Vanilla JS)

---

## Project Structure

```text
rag-study-companion/
│
├── app.py                      # Server entry point
├── config.py                   # Central configuration
├── requirements.txt            # Dependencies
├── .env.example                # Environment configuration template
├── .env                        # Local environment variables (git-ignored)
├── .gitignore
├── README.md                   # Documentation & phase tracking
│
├── app/
│   ├── __init__.py             # Flask app factory
│   │
│   ├── routes/
│   │   ├── main.py             # App index & health check
│   │   ├── documents.py        # PDF management & ingestion
│   │   ├── chat.py             # RAG QA endpoint
│   │   └── study.py            # Quiz, Flashcard & Summary endpoints
│   │
│   ├── services/               # Service implementations (PDF, Chroma, Embeddings, Groq, Agent)
│   ├── models/                 # Internal schemas
│   └── utils/                  # Helper utilities
│
├── templates/
│   └── index.html              # Academic workspace UI
│
├── static/
│   ├── css/
│   │   └── style.css           # Clean, restrained academic stylesheet
│   └── js/
│       └── app.js              # View navigation & state management
│
├── data/
│   ├── uploads/                # Stored raw documents
│   └── chroma/                 # ChromaDB persistent collection files
│
└── tests/                      # Pytest suite
```

---

## Setup & Running Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and set your `GROQ_API_KEY`:
```bash
GROQ_API_KEY=your_actual_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
```

### 3. Start the Server
```bash
python app.py
```
Open `http://localhost:5000` in your web browser.
