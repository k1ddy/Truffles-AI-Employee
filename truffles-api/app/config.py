from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://test:test@localhost:5432/test"
    debug: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
