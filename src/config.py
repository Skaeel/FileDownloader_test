from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class DBConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="DB_")

    HOST: str
    PORT: int
    NAME: str
    USER: str
    PASSWORD: SecretStr

    @property
    def DB_URL_asyncpg(self):
        return f"postgresql+asyncpg://{self.USER}:{self.PASSWORD.get_secret_value()}@{self.HOST}:{self.PORT}/{self.NAME}"


class APIConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="API_")

    HOST: str
    PORT: int


class TargetAPIConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="TARGET_API_")

    HOST: str
    PORT: int


class Config(BaseSettings):
    db: DBConfig = Field(default_factory=DBConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    target_api: TargetAPIConfig = Field(default_factory=TargetAPIConfig)


settings = Config()
