# Architecture Overview

## System Diagram

```
            ┌──────────────────────┐
            │      React.js        │
            │      Frontend        │
            └──────────┬───────────┘
                       │ HTTP
                       ▼
            ┌──────────────────────┐
            │  FastAPI  Backend    │
            │  /api/ingest         │
            │  /api/repos          │
            └──────────┬───────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   PostgreSQL       Neo4j          Qdrant
   (metadata)    (code graph)  (embeddings)
```

## Data Flow (Review 1)

```
GitHub URL
    │
    ▼
Clone Repository (GitPython)
    │
    ▼
Discover Python Files
    │  ignores: .git, __pycache__, venv, node_modules
    ▼
AST Parser (parser/ast_parser/parser.py)
    │  → functions, classes, imports, calls
    ▼
Code Chunker (parser/chunker/chunker.py)
    │  → one chunk per function/method
    ▼
    ├──────────────────────┐──────────────────────┐
    ▼                      ▼                      ▼
Neo4j Graph            Qdrant Vector           BM25 Index
(graph_builder.py)     (embedder.py)           (bm25_index.py)
```

## Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `backend/app/services/ingestion_service.py` | Orchestrates the whole pipeline |
| `parser/ast_parser/parser.py` | Python AST → structured data |
| `parser/chunker/chunker.py` | Structural code chunks |
| `graph/neo4j/graph_builder.py` | Writes to Neo4j |
| `retrieval/vector/embedder.py` | Generates + stores embeddings |
| `retrieval/bm25/bm25_index.py` | Builds + queries BM25 |

## Neo4j Schema

### Node Labels
- `File` — `{path: string}`
- `Function` — `{name, file, start_line, end_line}`
- `Class` — `{name, file, start_line, end_line}`
- `Module` — `{name}` (imported dependency)

### Relationship Types
- `CONTAINS` — File → Function/Class
- `HAS_METHOD` — Class → Function
- `CALLS` — Function → Function
- `IMPORTS` — File → Module

## Chunk Schema

```json
{
  "file": "auth.py",
  "symbol": "authenticate_user",
  "type": "function",
  "start_line": 20,
  "end_line": 38,
  "code": "def authenticate_user(...):\n    ..."
}
```
