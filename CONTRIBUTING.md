# Contributing — Git Workflow

## Branch Model

```
main
 └── develop
      ├── feature/parser
      ├── feature/ingestion
      ├── feature/chunking
      ├── feature/graph
      ├── feature/retrieval-foundation
      ├── test/parser
      ├── test/chunker
      └── test/pipeline
```

### Branch Purposes

| Branch | Role | Who merges into it |
|--------|------|--------------------|
| `main` | Stable milestone releases (Review 1, 2, 3) | Only from `develop` via PR after a milestone review |
| `develop` | Integration — always runnable | Feature + test branches via PR |
| `feature/parser` | AST parser implementation (`parser/ast_parser/`) | → `develop` |
| `feature/ingestion` | Repository cloning + file discovery (`backend/app/services/ingestion_service.py`) | → `develop` |
| `feature/chunking` | Code chunking (`parser/chunker/`) | → `develop` |
| `feature/graph` | Neo4j graph builder (`graph/neo4j/`) | → `develop` |
| `feature/retrieval-foundation` | Embedder, VectorStore, BM25 (`retrieval/`) | → `develop` |
| `test/parser` | Unit tests for the AST parser | → `develop` |
| `test/chunker` | Unit tests for the chunker | → `develop` |
| `test/pipeline` | Integration tests for the full pipeline | → `develop` |

---

## Day-to-Day Flow

### Starting work on a feature

```bash
git checkout develop
git pull origin develop          # always sync first
git checkout feature/parser      # or whichever feature branch
```

### Committing

Keep commits small and focused.  Use this prefix convention:

| Prefix | When to use |
|--------|-------------|
| `feat:` | new functionality |
| `fix:` | bug fix |
| `refactor:` | internal restructure, no behaviour change |
| `test:` | adding or updating tests |
| `docs:` | documentation only |
| `chore:` | tooling, deps, CI |

```bash
git add parser/ast_parser/parser.py
git commit -m "feat: extract function call graph from AST"
```

### Merging into develop

1. Push your branch:
   ```bash
   git push origin feature/parser
   ```
2. Open a Pull Request on GitHub: `feature/parser → develop`
3. Get at least one review and all tests passing
4. Squash-merge into `develop`

### Releasing a milestone (e.g. Review 1)

```bash
git checkout develop
git pull origin develop
# confirm all tests pass
git checkout main
git merge --no-ff develop -m "chore: Review 1 milestone release"
git push origin main
git tag -a v0.1.0-review1 -m "Review 1: Repository Intelligence Foundation"
git push origin --tags
```

---

## Rules

- **Never commit directly to `main`** — always go through `develop`
- **Never commit directly to `develop`** — always go through a feature/test PR
- `develop` must always stay in a runnable state
- Tests in `test/*` branches should pass before the corresponding `feature/*` merges
- Keep `data/raw/repos/` out of git (it's in `.gitignore`)

---

## Quick Reference

```bash
# See all branches
git branch -a

# Sync your feature branch with latest develop
git fetch origin
git rebase origin/develop

# Check what's different from develop
git log develop..HEAD --oneline
```
