from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "Savage Worlds Charakter-Generator"
    database_url: str = "sqlite:///./data/chargen.db"
    secret_key: str = "CHANGE-ME-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 Stunden

    gamelogic_path: Path = Path(__file__).resolve().parent.parent / "gamelogic"
    # Eigene Settings der Nutzer — liegt unter data/ (Docker-Volume), damit sie
    # App-Updates überleben (Original: user_settings_dir mit custom_*.json)
    custom_settings_path: Path = Path("data") / "settings"

    model_config = {"env_prefix": "CHARGEN_"}


settings = Settings()
