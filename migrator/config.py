from dataclasses import dataclass, field
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(os.environ.get("MIGRATOR_ROOT", Path(__file__).resolve().parents[1]))
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-5-mini"))
    api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""), repr=False)
    budget: int = field(default_factory=lambda: int(os.getenv("TOKEN_BUDGET", "500000")))
    max_attempts: int = field(default_factory=lambda: int(os.getenv("MAX_ATTEMPTS", "3")))
    max_output_tokens: int = field(
        default_factory=lambda: int(os.getenv("MAX_OUTPUT_TOKENS", "8192"))
    )
    sql_host: str = field(default_factory=lambda: os.getenv("SQLSERVER_HOST", "localhost"))
    sql_port: int = field(default_factory=lambda: int(os.getenv("SQLSERVER_PORT", "14330")))
    pg_host: str = field(default_factory=lambda: os.getenv("POSTGRES_HOST", "localhost"))
    pg_port: int = field(default_factory=lambda: int(os.getenv("POSTGRES_PORT", "54330")))
    sql_password: str = field(
        default_factory=lambda: os.getenv("SQLSERVER_PASSWORD", "LocalMigration!2026"), repr=False
    )
    pg_password: str = field(
        default_factory=lambda: os.getenv("POSTGRES_PASSWORD", "LocalMigration!2026"), repr=False
    )
    runner_password: str = field(
        default_factory=lambda: os.getenv("RUNNER_PASSWORD", "RunnerMigration!2026"), repr=False
    )

    @property
    def benchmark(self):
        return self.root / "benchmark"

    @property
    def artifacts(self):
        return self.root / "artifacts"

    def __post_init__(self):
        if self.budget < 1 or self.max_output_tokens < 1 or not 1 <= self.max_attempts <= 10:
            raise ValueError("Presupuesto y salida deben ser positivos; intentos entre 1 y 10.")


def redact(message: str, settings: Settings) -> str:
    for secret in [
        settings.api_key,
        settings.sql_password,
        settings.pg_password,
        settings.runner_password,
    ]:
        if secret:
            message = message.replace(secret, "[REDACTED]")
    return message
