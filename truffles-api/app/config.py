from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://test:test@localhost:5432/test"
    debug: bool = False

    # Policy-Core v3 PoC feature flag.
    # See SPECS/POLICY_CORE_V3.md. When False, the legacy intent_service path
    # owns runtime decisions. The PoC module is not wired even when True until
    # Phase B (shadow run); see spec section 8.
    policy_core_v3_enabled: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
