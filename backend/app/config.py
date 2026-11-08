from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "Savage Worlds Charakter-Generator"
    database_url: str = "sqlite:///./data/chargen.db"
    secret_key: str = "CHANGE-ME-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 Stunden
    # Swagger/ReDoc unter /api/docs — in Produktion per CHARGEN_API_DOCS=false aus
    api_docs: bool = True
    # Kommagetrennte E-Mails, die alle eigenen Settings bearbeiten dürfen
    # (auch die ohne Besitzer aus der Zeit vor der Besitzer-Prüfung)
    admin_emails: str = ""
    passwort_min_laenge: int = 8

    gamelogic_path: Path = Path(__file__).resolve().parent.parent / "gamelogic"
    # Eigene Settings der Nutzer — liegt unter data/ (Docker-Volume), damit sie
    # App-Updates überleben (Original: user_settings_dir mit custom_*.json)
    custom_settings_path: Path = Path("data") / "settings"
    # Charakterporträts (data/bilder/<user_id>/<bild_id>_<variante>.webp)
    bilder_path: Path = Path("data") / "bilder"
    bild_max_upload_mb: int = 8
    bild_kontingent_mb: int = 50
    # Eigene Settings gelten instanzweit — Obergrenzen gegen Vollschreiben
    settings_max_pro_nutzer: int = 25
    setting_max_mb: int = 5

    model_config = {"env_prefix": "CHARGEN_"}


settings = Settings()
