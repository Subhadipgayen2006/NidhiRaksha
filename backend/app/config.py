from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    database_url: str = "sqlite:///./nidhiraksha.db"
    secret_key: str = "local-demo-only"
    document_storage_path: str = "./storage"
    max_upload_mb: int = 10
    cors_origins: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings = Settings()
