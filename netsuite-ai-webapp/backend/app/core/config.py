from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    app_env: str = "dev"
    database_url: str = "postgresql+psycopg://postgres:postgres@postgres:5432/netsuite_ai"

    # Secret encryption (envelope encryption KEK; base64 for 32-byte AES-256 key)
    app_key_id: str = "v1"
    app_kek_b64: str = ""

    # NetSuite JDBC
    netsuite_jdbc_jar: str = ""
    netsuite_jdbc_jars: str = ""  # comma-separated list of additional JARs
    netsuite_jdbc_driver: str = "com.netsuite.jdbc.openaccess.OpenAccessDriver"
    netsuite_jdbc_row_limit: int = 50

    # LLM (SQL generation)
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"


settings = Settings()
