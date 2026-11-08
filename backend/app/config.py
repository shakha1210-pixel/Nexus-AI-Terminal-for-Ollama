from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NEXUS AI API"
    ollama_base_url: str = "http://127.0.0.1:11434"
    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    request_timeout_seconds: float = 8.0
    kaggle_username: str = ""
    kaggle_key: str = ""
    kaggle_kernel_name: str = "nexus-ollama-server"
    ngrok_domain: str = ""
    tunnel_user: str = "nexus"
    tunnel_password: str = ""
    openai_compatible_base_url: str = ""
    openai_compatible_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


settings = Settings()
