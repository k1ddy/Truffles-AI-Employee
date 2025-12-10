from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://n8n:Iddqd777!@postgres:5432/chatbot"
    debug: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
