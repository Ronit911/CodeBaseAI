from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://codebaseai:codebaseai@localhost:5432/codebaseai"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "codebaseai"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    REPO_CLONE_DIR: str = "./data/raw/repos"
    ALLOWED_EXTENSIONS: str = ".py"

    class Config:
        env_file = ".env"


settings = Settings()
