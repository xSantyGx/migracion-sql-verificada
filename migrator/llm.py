"""Strict Responses API output plus a persistent conservative spend ledger."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from filelock import FileLock
from openai import OpenAI, APIConnectionError, APIStatusError, APITimeoutError
from pydantic import ValidationError
from .config import redact
from .storage import write_json


class BudgetExceeded(RuntimeError):
    pass


class ModelFailure(RuntimeError):
    pass


def prompt(name):
    return (Path(__file__).parent / "prompts" / f"{name}.txt").read_text()


class LLM:
    def __init__(self, settings):
        if not settings.api_key:
            raise ModelFailure("Falta OPENAI_API_KEY en .env.")
        self.s = settings
        self.client = OpenAI(api_key=settings.api_key, max_retries=0, timeout=90)
        self.path = settings.artifacts / "usage.json"
        self.lock = FileLock(str(settings.artifacts / "usage.lock"), timeout=5)
        settings.artifacts.mkdir(parents=True, exist_ok=True)

    def usage(self):
        return (
            json.loads(self.path.read_text())
            if self.path.exists()
            else {"limit": self.s.budget, "charged_tokens": 0, "calls": []}
        )

    def call(self, system, content, schema, purpose, max_output=None):
        inputs = [{"role": "system", "content": system}, {"role": "user", "content": content}]
        output_limit = max_output or self.s.max_output_tokens
        text = (
            {
                "format": {
                    "type": "json_schema",
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                    "strict": True,
                }
            }
            if schema
            else {"format": {"type": "text"}}
        )
        # Count with the server, including the strict response schema.
        for count_attempt in range(3):
            try:
                counted = self.client.responses.input_tokens.count(
                    model=self.s.model, input=inputs, text=text
                )
                break
            except (APIConnectionError, APIStatusError) as error:
                transient = (
                    isinstance(error, APIConnectionError)
                    or error.status_code in {408, 409, 429}
                    or error.status_code >= 500
                )
                if not transient or count_attempt == 2:
                    raise ModelFailure(
                        "No se pudo contar tokens: " + redact(str(error), self.s)
                    ) from error
                time.sleep(count_attempt + 1)
        reservation = counted.input_tokens + output_limit
        with self.lock:
            ledger = self.usage()
            ledger["limit"] = self.s.budget
            if ledger["charged_tokens"] + reservation > self.s.budget:
                raise BudgetExceeded("La siguiente llamada excedería el presupuesto restante.")
            index = len(ledger["calls"])
            record = {
                "purpose": purpose,
                "model": self.s.model,
                "reserved_tokens": reservation,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            ledger["calls"].append(record)
            ledger["charged_tokens"] += reservation
            write_json(self.path, ledger)
        started = time.monotonic()
        response = None
        try:
            response = self.client.responses.create(
                model=self.s.model,
                input=inputs,
                text=text,
                max_output_tokens=output_limit,
                reasoning={"effort": "low"},
                store=False,
            )
            usage = response.usage.model_dump() if response.usage else None
            with self.lock:
                ledger = self.usage()
                if usage:
                    ledger["charged_tokens"] += usage["total_tokens"] - reservation
                ledger["calls"][index].update(
                    status=response.status,
                    usage=usage,
                    response_id=response.id,
                    elapsed_seconds=round(time.monotonic() - started, 3),
                )
                write_json(self.path, ledger)
            if response.status != "completed":
                raise ModelFailure("Respuesta incompleta: " + str(response.incomplete_details))
            parsed = (
                schema.model_validate_json(response.output_text) if schema else response.output_text
            )
            metadata = {
                "call_index": index,
                "model": response.model,
                "response_id": response.id,
                "usage": usage,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "raw_output": response.output_text,
            }
            return parsed, metadata
        except (
            APIConnectionError,
            APIStatusError,
            APITimeoutError,
            ValidationError,
            ModelFailure,
        ) as error:
            with self.lock:
                ledger = self.usage()
                ledger["calls"][index].update(
                    status="error",
                    error=redact(str(error), self.s),
                    elapsed_seconds=round(time.monotonic() - started, 3),
                )
                # Unknown transport outcome: keep reserved maximum; never spend it twice.
                write_json(self.path, ledger)
            raise ModelFailure(redact(str(error), self.s)) from error
