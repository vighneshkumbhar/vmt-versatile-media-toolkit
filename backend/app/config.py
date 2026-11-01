from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"  # "development" | "production"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    PASSWORD_PEPPER: str = "dev-password-pepper-change-in-production"
    ADMIN_BOOTSTRAP_SECRET: str = "dev-admin-bootstrap-secret"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    STORAGE_BACKEND: str = "local"       # "local" | "s3"
    LOCAL_STORAGE_PATH: str = "./package_storage"
    QUARANTINE_PATH: str = "./quarantine"
    DATABASE_URL: str = "sqlite+aiosqlite:///./vmt_ecosystem.db"
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    CORS_ORIGINS: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 5
    RATE_LIMIT_SUBMIT_PER_HOUR: int = 10
    ARGON2_TIME_COST: int = 3
    ARGON2_MEMORY_COST: int = 65536
    ARGON2_PARALLELISM: int = 4
    
    class Config:
        env_file = ".env"

settings = Settings()
