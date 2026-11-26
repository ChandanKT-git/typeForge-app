"""LLM Observability & Tracing wrapper using Langfuse (Phase 4).

WHY THIS MODULE EXISTS:
  In production AI engineering, an LLM call is not a black box. Every call needs
  to be observable across:
    1. Latency (ms): How long the user waited for Groq to generate a passage.
    2. Prompts & Outputs: Exact system prompt, user prompt, and structured JSON output
       so we can debug bad generations or prompt regressions.
    3. Token & Cost Estimation: Input and output token counts per endpoint/model.
    4. User & Domain Attribution: Which user, domain, topic, or RAG document chunks
       triggered the call.
    5. Side-Channel Fault Isolation: If Langfuse is unconfigured or unreachable,
       tracing degrades gracefully to a no-op and NEVER breaks the user's request.
"""

from collections import deque
from datetime import datetime, timezone
import logging
import os
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger("typeforge.observability")

_langfuse = None
# In-memory ring buffer of recent traces (useful for local inspection & automated tests)
_recent_traces: Deque[Dict[str, Any]] = deque(maxlen=100)


def _get_langfuse():
    """Lazy-initialize the Langfuse SDK client.

    Returns None if LANGFUSE_SECRET_KEY is not set in the environment, allowing
    local development and CI to run without external credentials.
    """
    global _langfuse
    if _langfuse is None:
        secret = os.environ.get("LANGFUSE_SECRET_KEY")
        if not secret:
            return None
        try:
            from langfuse import Langfuse

            _langfuse = Langfuse(
                secret_key=secret,
                public_key=os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
                host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
            )
        except Exception as exc:
            logger.warning("Langfuse initialization skipped: %s", exc)
            return None
    return _langfuse


def _estimate_tokens(text: str) -> int:
    """Fast heuristic token estimator (~4 chars per token for English/code)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def get_recent_traces() -> List[Dict[str, Any]]:
    """Return a list of the most recent recorded LLM trace events (up to 100)."""
    return list(_recent_traces)


def clear_recent_traces() -> None:
    """Clear the in-memory trace buffer (used by test fixtures)."""
    _recent_traces.clear()


def trace_llm_call(
    name: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    output: str,
    latency_ms: float,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    status: str = "success",
    error_message: Optional[str] = None,
) -> None:
    """Record an LLM call as an observability trace and Langfuse generation span.

    SIDE-CHANNEL GUARANTEE:
      Wrapped in `try / except Exception: pass` so an observability error or
      network blip to Langfuse Cloud can never crash or slow down a user's
      typing session.
    """
    try:
        input_tokens = _estimate_tokens(system_prompt) + _estimate_tokens(user_prompt)
        output_tokens = _estimate_tokens(output)
        meta = dict(metadata or {})
        meta.update(
            {
                "latency_ms": round(latency_ms, 2),
                "status": status,
                "estimated_input_tokens": input_tokens,
                "estimated_output_tokens": output_tokens,
                "estimated_total_tokens": input_tokens + output_tokens,
            }
        )
        if error_message:
            meta["error"] = error_message

        # 1. Record in local ring buffer for instant inspection & diagnostics
        _recent_traces.append(
            {
                "name": name,
                "model": model,
                "user_id": user_id,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "output": output,
                "latency_ms": round(latency_ms, 2),
                "status": status,
                "error_message": error_message,
                "metadata": meta,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        # 2. Export to Langfuse if configured
        lf = _get_langfuse()
        if lf is None:
            return

        trace = lf.trace(
            name=name,
            user_id=user_id,
            metadata=meta,
        )
        trace.generation(
            name=f"{name}_generation",
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            output=output,
            usage={
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens,
            },
            level="ERROR" if status == "error" else "DEFAULT",
            status_message=error_message,
            metadata=meta,
        )
    except Exception:
        # Observability is strictly a non-blocking side-channel
        pass
