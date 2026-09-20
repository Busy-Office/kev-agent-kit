"""STDIO MCP adapter; only the HTTP service loads model weights."""
import json
import os
from pathlib import Path
import sys
from typing import Annotated

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

# Reuse Kev's canonical request schema without importing torch or its server.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from kev.api import JSONContent, Question, SystemOneRequest

BASE_URL = os.environ.get("KEV_BASE_URL", "http://127.0.0.1:8008").rstrip("/")
TIMEOUT = float(os.environ.get("KEV_TIMEOUT_SECONDS", "90"))
mcp = FastMCP("kev", instructions=(
    "Kev returns probabilities for typed classification questions. These are advisory; "
    "coding-task calibration is unverified. Inspect evidence and run tests before acting. "
    "Use kev_models to check availability. Batch independent questions about one state. "
    "Do not treat confidence as probability of correctness or authorization to act."
))
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)


async def request(method: str, path: str, body: dict | None = None) -> dict:
    if body is not None and len(json.dumps(body).encode()) > 64_000:
        raise ValueError("Request exceeds 64 KB; summarize or split the state.")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, trust_env=False) as client:
            response = await client.request(method, BASE_URL + path, json=body)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException as exc:
        raise RuntimeError("Kev timed out; shorten the state or retry after the current inference finishes.") from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"Kev returned HTTP {exc.response.status_code}: {exc.response.text[:1000]}") from exc
    except httpx.RequestError as exc:
        raise RuntimeError("Kev is unavailable. Start docker compose up -d --build and check docker compose logs kev.") from exc


def payload(state: JSONContent, questions: dict[str, Question]) -> dict:
    if not 1 <= len(questions) <= 16:
        raise ValueError("Provide 1–16 questions per call.")
    return SystemOneRequest(state=state, questions=questions).model_dump(mode="json")


@mcp.tool(annotations=READ_ONLY)
async def kev_models() -> dict:
    """Check the running Kev checkpoint and base model. Does not download or start models."""
    return await request("GET", "/v1/models")


@mcp.tool(annotations=READ_ONLY)
async def kev_decide(state: JSONContent, questions: dict[str, Question]) -> dict:
    """Evaluate 1–16 independent questions about one state. Types: noul (yes/no probability),
    choice (named criteria and probabilities), score (ordered criteria, zero-based expected level).
    Returns the original distributions, confidence and inference latency. Coding judgments are experimental.
    """
    return await request("POST", "/v1/systemone", payload(state, questions))


@mcp.tool(annotations=READ_ONLY)
async def kev_check_permutations(
    state: JSONContent,
    questions: dict[str, Question],
    question: str,
    n_perm: Annotated[int, Field(ge=2, le=8)] = 3,
    seed: int = 0,
) -> dict:
    """Check one choice question for sensitivity to option order (2–8 sequential passes).
    Stable choices are not proof of correctness. Other questions are not evaluated.
    """
    data = payload(state, questions)
    selected = data["questions"].get(question)
    if selected is None or selected["type"] != "choice":
        raise ValueError("question must name an existing choice question")
    return await request("POST", "/v1/systemone/permute", {
        "request": data, "question": question, "n_perm": n_perm, "seed": seed,
    })


if __name__ == "__main__":
    mcp.run(transport="stdio")
