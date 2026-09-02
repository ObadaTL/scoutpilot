"""
Unified LLM client for ScoutPilot.

Auto-detects provider from environment:
  GEMINI_API_KEY  -> Google Gemini (default: gemini-2.0-flash)
  OPENAI_API_KEY  -> OpenAI (default: gpt-4o-mini)
  LLM_URL         -> Local llama.cpp / Ollama compatible endpoint

LLM_MODEL env var overrides the model name for any provider.
"""

import logging
import os
import time

import httpx

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider detection
# ---------------------------------------------------------------------------

def is_local_provider() -> bool:
    """True when generation will hit a local (non-cloud) LLM_URL endpoint.

    Mirrors _detect_provider's own precedence (LLM_URL wins over any cloud
    API key when both are set) without constructing a client. Used to
    auto-tune retry/judge behavior for tailoring: a small local model
    doesn't reliably improve on repeated "avoid these issues" retries the
    way a cloud model does, and a same-size local model judging its own
    output adds latency without much of a trust bump -- see tailor.py.
    """
    return bool(os.environ.get("LLM_URL", ""))


def _detect_provider() -> tuple[str, str, str]:
    """Return (base_url, model, api_key) based on environment variables.

    Reads env at call time (not module import time) so that load_env() called
    in _bootstrap() is always visible here.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    local_url = os.environ.get("LLM_URL", "")
    model_override = os.environ.get("LLM_MODEL", "")

    if gemini_key and not local_url:
        return (
            "https://generativelanguage.googleapis.com/v1beta/openai",
            # "gemini-2.0-flash" is a pinned dated model id and has since
            # been retired by Google (confirmed via /v1beta/models -- it no
            # longer appears in the account's available model list, so the
            # native generateContent call 404s). "-latest" is Google's
            # rolling alias for the current recommended flash model, so this
            # default won't go stale the same way again.
            model_override or "gemini-flash-latest",
            gemini_key,
        )

    if openai_key and not local_url:
        return (
            "https://api.openai.com/v1",
            model_override or "gpt-4o-mini",
            openai_key,
        )

    if local_url:
        return (
            local_url.rstrip("/"),
            model_override or "local-model",
            os.environ.get("LLM_API_KEY", ""),
        )

    raise RuntimeError(
        "No LLM provider configured. "
        "Set GEMINI_API_KEY, OPENAI_API_KEY, or LLM_URL in your environment."
    )


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

_MAX_RETRIES = 5
_TIMEOUT = 120  # seconds

# Base wait on first 429/503 (doubles each retry, caps at 60s).
# Gemini free tier is 15 RPM = 4s minimum between requests; 10s gives headroom.
_RATE_LIMIT_BASE_WAIT = 10


_GEMINI_COMPAT_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
_GEMINI_NATIVE_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Ollama's runtime context window defaults to 4096 tokens for ANY model
# unless a request explicitly overrides it with `options.num_ctx` -- this is
# independent of the model's own max supported context (qwen3:14b supports
# 40960). Confirmed live 2026-08-24: the tailoring prompt alone (system
# prompt + base resume + a near-6000-char job description) already runs
# ~4900 tokens, before the ~2048-token output budget is even added -- well
# past the silent-truncation point, on every call, for any job with a
# moderately long description. Verified 8192 fits this machine's 16GB card
# with ~3GB of headroom to spare (peak ~13.2GB during generation).
# LLM_NUM_CTX lets a smaller/larger card override it.
_DEFAULT_NUM_CTX = 8192


class LLMClient:
    """Thin LLM client supporting OpenAI-compatible and native Gemini endpoints.

    For Gemini keys, starts on the OpenAI-compat layer. On a 403 (which
    happens with preview/experimental models not exposed via compat), it
    automatically switches to the native generateContent API and stays there
    for the lifetime of the process.
    """

    def __init__(self, base_url: str, model: str, api_key: str) -> None:
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self._client = httpx.Client(timeout=_TIMEOUT)
        # True once we've confirmed the native Gemini API works for this model
        self._is_gemini: bool = base_url.startswith(_GEMINI_COMPAT_BASE)
        # Use native generateContent API directly for Gemini
        self._use_native_gemini: bool = self._is_gemini
        self._num_ctx = int(os.environ.get("LLM_NUM_CTX", _DEFAULT_NUM_CTX))

    # -- Native Gemini API --------------------------------------------------

    def _chat_native_gemini(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call the native Gemini generateContent API.

        Used automatically when the OpenAI-compat endpoint returns 403,
        which happens for preview/experimental models not exposed via compat.

        Converts OpenAI-style messages to Gemini's contents/systemInstruction
        format transparently.
        """
        contents: list[dict] = []
        system_parts: list[dict] = []

        for msg in messages:
            role = msg["role"]
            text = msg.get("content", "")
            if role == "system":
                system_parts.append({"text": text})
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": text}]})
            elif role == "assistant":
                # Gemini uses "model" instead of "assistant"
                contents.append({"role": "model", "parts": [{"text": text}]})

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}

        url = f"{_GEMINI_NATIVE_BASE}/models/{self.model}:generateContent"
        resp = self._client.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            params={"key": self.api_key},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    # -- OpenAI-compat API --------------------------------------------------

    def _chat_compat(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        json_schema: dict | None = None,
    ) -> str:
        """Call the OpenAI-compatible endpoint.

        json_schema, when given, is passed as `response_format` -- Ollama's
        OpenAI-compat layer (0.5+) constrains token sampling to match it, so
        the model literally cannot emit a differently-shaped JSON object.
        This is enforcement, not a prompt suggestion: it's what actually
        fixes a small local model inventing its own nested structure instead
        of the flat schema the prompt asks for (observed with qwen3:14b).
        """
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_schema is not None:
            payload["response_format"] = {"type": "json_schema", "json_schema": {"schema": json_schema}}

        resp = self._client.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers,
        )

        # 403 on Gemini compat = model not available on compat layer.
        # Raise a specific sentinel so chat() can switch to native API.
        if resp.status_code == 403 and self._is_gemini:
            raise _GeminiCompatForbidden(resp)

        return self._handle_compat_response(resp)

    @staticmethod
    def _handle_compat_response(resp: httpx.Response) -> str:
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]["message"]
        content = choice.get("content") or ""
        if not content and choice.get("reasoning"):
            content = choice.get("reasoning")
        return content

    # -- Ollama native API ----------------------------------------------------

    def _chat_ollama_native(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        json_schema: dict | None = None,
    ) -> str:
        """Call Ollama's native /api/chat, optionally with a JSON-schema `format`.

        Originally used only for schema-constrained calls, since Ollama's
        OpenAI-compat layer (/v1/chat/completions) silently ignores
        `response_format` on this build -- no error, but no enforcement
        either (verified empirically: the model's raw chain-of-thought came
        back as "content" instead of schema-shaped JSON). The native API's
        top-level `format: <schema>` field genuinely constrains sampling
        (also verified empirically) and cleanly separates "thinking" from
        "content".

        Now also the route for EVERY local call, schema or not: this is the
        only endpoint that accepts `options.num_ctx` -- the OpenAI-compat
        body has no field for it -- and without it Ollama silently runs at
        its own 4096-token default regardless of what the model actually
        supports (see _DEFAULT_NUM_CTX). A scoring or cover-letter call with
        no json_schema still needs that override just as much as a
        schema-constrained tailoring call does.

        Same [{role, content}, ...] message shape as the OpenAI-compat
        layer -- only the envelope differs.

        Also sets the top-level `think: false` field. The text-based
        `/no_think` prompt prefix (see chat()) does NOT reliably suppress
        qwen3's reasoning on this Ollama build -- confirmed live 2026-08-24:
        with `/no_think` prepended and num_predict=250, the model still
        spent the entire budget on hidden `message.thinking` and emitted 0-18
        chars of real `message.content` before hitting the length cap.
        Ollama's native `think` field is what actually works: same prompt,
        same budget, `think: false` produced 0 thinking tokens and 400-500+
        chars of real content, using under half the total tokens. Every
        max_tokens budget in this codebase (tailor, judge, score, cover
        letter) was sized assuming /no_think was working -- without this,
        those calls were burning most or all of their budget on invisible
        reasoning and returning truncated or empty JSON, which reads back
        as "not valid JSON" retries or malformed output, not as a reasoning
        problem.
        """
        url = self.base_url[: -len("/v1")] if self.base_url.endswith("/v1") else self.base_url
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {"temperature": temperature, "num_predict": max_tokens, "num_ctx": self._num_ctx},
        }
        if json_schema is not None:
            payload["format"] = json_schema
        resp = self._client.post(f"{url}/api/chat", json=payload, headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        data = resp.json()
        message = data["message"]
        content = message.get("content") or ""
        if not content and message.get("thinking"):
            # think:false should make this unreachable, but if an older
            # Ollama/model build ignores the field and reasons anyway, fall
            # back to it rather than return an empty string outright -- same
            # safety net _handle_compat_response already has.
            content = message["thinking"]
        return content

    # -- public API ---------------------------------------------------------

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.0,
        max_tokens: int = 4096,
        json_schema: dict | None = None,
    ) -> str:
        """Send a chat completion request and return the assistant message text.

        json_schema: optional JSON Schema to constrain the response to.
        Honored on Ollama's native path (_chat_ollama_native) and the
        OpenAI-compat path (_chat_compat) -- the native Gemini path ignores
        it (Gemini's own JSON mode has been reliable enough in practice
        that this hasn't been needed there).
        """
        # Qwen3: prepend /no_think as a secondary hint for any Qwen served
        # over the OpenAI-compat path (cloud or a non-Ollama local server),
        # where there's no equivalent to Ollama's native `think` field to
        # rely on instead. NOT the primary mechanism for a local Ollama
        # provider -- confirmed live 2026-08-24 that this text convention
        # does not reliably suppress qwen3's reasoning on this Ollama build
        # (the model still spent its whole token budget on hidden
        # "thinking" and returned little/no real content); the native path
        # (_chat_ollama_native) sets `think: false` instead, which does
        # work. Every call site in this codebase sends [system, user, ...]
        # -- looking only at messages[0] (as this used to) means the role
        # is always "system" there and this never fires. Find the first
        # "user" message wherever it actually is instead.
        if "qwen" in self.model.lower() and messages:
            for i, msg in enumerate(messages):
                if msg.get("role") == "user":
                    if not msg["content"].startswith("/no_think"):
                        messages = list(messages)
                        messages[i] = {**msg, "content": f"/no_think\n{msg['content']}"}
                    break

        for attempt in range(_MAX_RETRIES):
            try:
                # Route to native Gemini if we've already confirmed it's needed
                if self._use_native_gemini:
                    return self._chat_native_gemini(messages, temperature, max_tokens)

                # Every call to a local (non-Gemini) provider goes through
                # Ollama's native /api/chat -- not just schema-constrained
                # ones. Besides being where `format` actually enforces a
                # schema (see _chat_ollama_native), it's the only endpoint
                # that accepts `options.num_ctx`; the OpenAI-compat body has
                # no field for it, so a plain (no-schema) compat call to
                # Ollama silently runs at its 4096-token default regardless
                # of what the model supports. json_schema is passed through
                # as-is (None is fine -- see _chat_ollama_native).
                if not self._is_gemini:
                    try:
                        return self._chat_ollama_native(messages, temperature, max_tokens, json_schema)
                    except Exception:
                        log.warning(
                            "Ollama native /api/chat call failed (not Ollama, or an "
                            "old version) -- falling back to OpenAI-compat generation "
                            "(num_ctx override and, if requested, schema enforcement "
                            "are both lost on this fallback path).",
                            exc_info=True,
                        )
                        return self._chat_compat(messages, temperature, max_tokens, json_schema=json_schema)

                return self._chat_compat(messages, temperature, max_tokens, json_schema=json_schema)

            except _GeminiCompatForbidden as exc:
                # Model not available on OpenAI-compat layer — switch to native.
                log.warning(
                    "Gemini compat endpoint returned 403 for model '%s'. "
                    "Switching to native generateContent API. "
                    "(Preview/experimental models are often compat-only on native.)",
                    self.model,
                )
                self._use_native_gemini = True
                # Retry immediately with native — don't count as a rate-limit wait
                try:
                    return self._chat_native_gemini(messages, temperature, max_tokens)
                except httpx.HTTPStatusError as native_exc:
                    raise RuntimeError(
                        f"Both Gemini endpoints failed. Compat: 403 Forbidden. "
                        f"Native: {native_exc.response.status_code} — "
                        f"{native_exc.response.text[:200]}"
                    ) from native_exc

            except httpx.HTTPStatusError as exc:
                resp = exc.response
                if resp.status_code in (429, 503) and attempt < _MAX_RETRIES - 1:
                    # Respect Retry-After header if provided (Gemini sends this).
                    retry_after = (
                        resp.headers.get("Retry-After")
                        or resp.headers.get("X-RateLimit-Reset-Requests")
                    )
                    if retry_after:
                        try:
                            wait = float(retry_after)
                        except (ValueError, TypeError):
                            wait = _RATE_LIMIT_BASE_WAIT * (2 ** attempt)
                    else:
                        wait = min(_RATE_LIMIT_BASE_WAIT * (2 ** attempt), 60)

                    log.warning(
                        "LLM rate limited (HTTP %s). Waiting %ds before retry %d/%d. "
                        "Tip: Gemini free tier = 15 RPM. Consider a paid account "
                        "or switching to a local model.",
                        resp.status_code, wait, attempt + 1, _MAX_RETRIES,
                    )
                    time.sleep(wait)
                    continue
                raise

            except httpx.TimeoutException:
                if attempt < _MAX_RETRIES - 1:
                    wait = min(_RATE_LIMIT_BASE_WAIT * (2 ** attempt), 60)
                    log.warning(
                        "LLM request timed out, retrying in %ds (attempt %d/%d)",
                        wait, attempt + 1, _MAX_RETRIES,
                    )
                    time.sleep(wait)
                    continue
                raise

        raise RuntimeError("LLM request failed after all retries")

    def ask(self, prompt: str, **kwargs) -> str:
        """Convenience: single user prompt -> assistant response."""
        return self.chat([{"role": "user", "content": prompt}], **kwargs)

    def close(self) -> None:
        self._client.close()


class _GeminiCompatForbidden(Exception):
    """Sentinel: Gemini OpenAI-compat returned 403. Switch to native API."""
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        super().__init__(f"Gemini compat 403: {response.text[:200]}")


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_instance: LLMClient | None = None


def get_client() -> LLMClient:
    """Return (or create) the module-level LLMClient singleton."""
    global _instance
    if _instance is None:
        base_url, model, api_key = _detect_provider()
        log.info("LLM provider: %s  model: %s", base_url, model)
        _instance = LLMClient(base_url, model, api_key)
    return _instance
