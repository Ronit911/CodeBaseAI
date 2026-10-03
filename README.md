# CodeBaseAI 🧠

> A codebase-intelligence chatbot that ingests any Python GitHub repository and lets you ask questions about it — with citations.

## Architecture

```
            ┌──────────────────────┐
            │      React.js        │
            │      Frontend        │
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │       FastAPI        │
            │       Backend        │
            └──────────┬───────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   PostgreSQL       Neo4j          Qdrant
   Metadata       Code Graph    Vector Store
        │              │              │
        └──────────────┼──────────────┘
                       │
                       ▼
               Hybrid Retrieval
            ┌──────────┼──────────┐
            │          │          │
         Vector       BM25       Graph
            │          │          │
            └──────────┼──────────┘
                       ▼
                   Reranker
                       │
                       ▼
                      LLM
                       │
                       ▼
             Answer + Citations
```

## Project Layout

```
CodeBaseAI/
├── frontend/          # React.js chat UI
├── backend/           # FastAPI REST API
├── parser/            # AST parser + code chunker
├── graph/             # Neo4j schema + ingestion
├── retrieval/         # Vector, BM25, hybrid search
├── tests/             # Unit & integration tests
├── data/              # Raw repos, processed chunks, embeddings
├── docs/              # Architecture docs, API reference
├── docker-compose.yml
├── README.md
└── .gitignore
```

## Development Stages

| Stage | Goal |
|-------|-------|
| **Review 1** | Repository Intelligence Foundation — ingest a repo and build a machine-readable representation |
| **Review 2** | Retrieval pipeline — hybrid search (vector + BM25 + graph) + reranker |
| **Review 3** | Full chatbot — LLM integration, React UI, citations |

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### 1. Clone and configure
```bash
git clone https://github.com/Ronit911/CodeBaseAI.git
cd CodeBaseAI
cp .env.example .env   # fill in API keys
```

### 2. Start all services
```bash
docker-compose up -d
```

### 3. Run the backend (dev mode)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 4. Run the frontend (dev mode)
```bash
cd frontend
npm install
npm start
```

## API Endpoints (Review 1)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/ingest` | Accept a GitHub URL and start ingestion |
| `GET`  | `/api/repos/{repo_id}` | Get repo metadata |
| `GET`  | `/api/repos/{repo_id}/files` | List parsed files |
| `GET`  | `/api/repos/{repo_id}/graph` | Get graph summary |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React.js, Axios |
| Backend | FastAPI, SQLAlchemy |
| Metadata DB | PostgreSQL |
| Code Graph | Neo4j |
| Vector Store | Qdrant |
| Embeddings | sentence-transformers |
| BM25 | rank_bm25 |
| Parser | Python `ast` module |
