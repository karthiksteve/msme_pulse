'''\
LLM Explanation Service
=======================

This module provides a thin wrapper around a locally‑hosted LLM (Qwen2.5‑7B‑Instruct) served via LM Studio's OpenAI‑compatible API. It is responsible for:

* Building the strict system and user prompts required to generate credit‑eligible narratives.
* Making an async ``httpx`` request with retry logic and timeout handling.
* Parsing the JSON response, validating required keys, and performing lightweight sanity checks.
* Exposing a ``health_check`` method used by the ``/health`` endpoint.

The service deliberately **fails open** – callers catch ``LLMUnavailableError`` or ``LLMResponseParseError`` and fall back to the deterministic template‑based explanations in ``xai_service.py``.
'''\

import json
import logging
import re
import time
import asyncio
from typing import Any, Dict, List

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMUnavailableError(Exception):
    """Raised when LM Studio's server cannot be reached or is disabled."""


class LLMResponseParseError(Exception):
    """Raised when the LLM's response cannot be parsed into the expected JSON schema."""


class LLMExplainerService:
    """Generate narrative text for MSME loan eligibility using a local LLM.

    The service **does not** compute any numeric values – it only turns the already‑
    computed facts into fluent prose. All numeric integrity checks are performed by
    the caller (``XAILoanService``).
    """

    def __init__(self) -> None:
        self.base_url: str = settings.LM_STUDIO_BASE_URL.rstrip('/')
        self.model: str = settings.LM_STUDIO_MODEL
        self.timeout_seconds: float = settings.LM_STUDIO_TIMEOUT_SECONDS
        self.enabled: bool = settings.LM_STUDIO_ENABLED
        # A single retry is enough to absorb a transient load‑time hiccup.
        self.max_retries: int = getattr(settings, 'LM_STUDIO_MAX_RETRIES', 1)

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    async def generate_xai_narrative(
        self,
        *,
        msme_data: Dict[str, Any],
        eligibility_score: float,
        band: str,
        eligibility_label: str,
        sub_scores: Dict[str, float],
        sub_score_labels: Dict[str, str],
        all_meta: Dict[str, Dict],
        rep_meta: Dict,
        rev_meta: Dict,
        computed_max_loan: float,
        asking_amount: float,
        is_eligible: bool,
    ) -> Dict[str, Any]:
        """Generate a JSON‑structured narrative.

        Routes to LM Studio if enabled, and falls back to Google Gemini if configured.
        """
        system_prompt, user_prompt = self._build_prompt(
            msme_data=msme_data,
            eligibility_score=eligibility_score,
            band=band,
            eligibility_label=eligibility_label,
            sub_scores=sub_scores,
            sub_score_labels=sub_score_labels,
            all_meta=all_meta,
            rep_meta=rep_meta,
            rev_meta=rev_meta,
            computed_max_loan=computed_max_loan,
            asking_amount=asking_amount,
            is_eligible=is_eligible,
        )

        if self.enabled:
            try:
                raw_content = await self._call_lm_studio(system_prompt, user_prompt)
                parsed = self._parse_and_validate(raw_content)
                parsed["narrative_source"] = "llm_studio"
                return parsed
            except Exception as e:
                logger.warning("LM Studio call failed, attempting Google Gemini fallback: %s", e)
                if settings.GEMINI_API_KEY:
                    raw_content = await self._call_gemini(system_prompt, user_prompt)
                    parsed = self._parse_and_validate(raw_content)
                    parsed["narrative_source"] = "google_gemini"
                    return parsed
                raise e
        else:
            if settings.GEMINI_API_KEY:
                raw_content = await self._call_gemini(system_prompt, user_prompt)
                parsed = self._parse_and_validate(raw_content)
                parsed["narrative_source"] = "google_gemini"
                return parsed
            else:
                raise LLMUnavailableError(
                    "LM Studio disabled and GEMINI_API_KEY is not set."
                )

    async def health_check(self) -> bool:
        """Lightweight check that either LM Studio or Google Gemini is healthy.

        Returns ``True`` if any configured LLM service is responsive.
        """
        if self.enabled:
            try:
                async with httpx.AsyncClient(timeout=3) as client:
                    resp = await client.get(f"{self.base_url}/models")
                    if resp.status_code == 200:
                        data = resp.json().get('data', [])
                        if data:
                            return True
            except Exception as e:
                logger.warning('LM Studio health check failed: %s', e)

        if settings.GEMINI_API_KEY:
            # Check if we can reach Google API (lightweight check)
            try:
                model = settings.GEMINI_MODEL
                async with httpx.AsyncClient(timeout=3) as client:
                    # just hit the model details endpoint to check API key / connection
                    resp = await client.get(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}?key={settings.GEMINI_API_KEY}"
                    )
                    if resp.status_code == 200:
                        return True
            except Exception as e:
                logger.warning('Google Gemini health check failed: %s', e)

        return False

    async def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        """Send the content generation request to Google Gemini API."""
        if not settings.GEMINI_API_KEY:
            raise LLMUnavailableError("GEMINI_API_KEY is not set.")

        model = settings.GEMINI_MODEL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.GEMINI_API_KEY}"
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1000,
                "responseMimeType": "application/json"
            }
        }

        attempt = 0
        while True:
            attempt += 1
            start = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.post(url, json=payload)
                elapsed = time.perf_counter() - start
                logger.debug(
                    "Google Gemini request payload size %d bytes, elapsed %.2f s, attempt %d",
                    len(json.dumps(payload).encode('utf-8')),
                    elapsed,
                    attempt,
                )
                if resp.status_code != 200:
                    raise LLMUnavailableError(
                        f"Google Gemini returned HTTP {resp.status_code}: {resp.text}"
                    )
                try:
                    content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return content
                except (KeyError, IndexError, json.JSONDecodeError) as e:
                    raise LLMResponseParseError(
                        f"Unexpected Google Gemini response shape: {resp.text}"
                    ) from e
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                logger.warning(
                    "Google Gemini call failed (%s) on attempt %d – retrying if possible",
                    type(e).__name__,
                    attempt,
                )
                if attempt > self.max_retries:
                    raise LLMUnavailableError('Google Gemini API unreachable after retries') from e
                await asyncio.sleep(0.2)

    # ---------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------
    def _build_prompt(
        self,
        *,
        msme_data: Dict[str, Any],
        eligibility_score: float,
        band: str,
        eligibility_label: str,
        sub_scores: Dict[str, float],
        sub_score_labels: Dict[str, str],
        all_meta: Dict[str, Dict],
        rep_meta: Dict,
        rev_meta: Dict,
        computed_max_loan: float,
        asking_amount: float,
        is_eligible: bool,
    ) -> tuple[str, str]:
        """Construct the strict system and user prompts.

        The prompts follow the exact wording from the specification (section 4).
        """
        # -------- System prompt ------------------------------------------------
        system_prompt = (
            "You are a senior MSME (Micro, Small & Medium Enterprise) credit underwriting analyst at an Indian bank, "
            "writing explanations of automated loan‑eligibility decisions for two audiences at once: (1) the loan officer "
            "reviewing the case, and (2) the business owner who will read a simplified version of this. Your writing must be:\n"
            "- Strictly grounded in the facts provided to you. NEVER invent, estimate, round differently, or restate any number "
            "differently than given. If a number is not given to you, do not mention a number for that concept at all – describe it "
            "qualitatively instead.\n"
            "- Professional, calm, and precise – banking tone, not marketing tone. No hype, no exclamation marks, no emoji.\n"
            "- Written in clear business English suitable for both a bank underwriter and a small‑business owner with no finance "
            "background.\n"
            "- Free of any recommendation to break rules, falsify GST filings, or engage in illegal or unethical financial behavior.\n"
            "- Output ONLY a single valid JSON object and nothing else – no preamble, no markdown code fences, no explanation of what you "
            "are about to do, no trailing commentary after the JSON. Your entire response must be parseable by a strict JSON parser as‑is.\n"
            "\n"
            "You will be given a structured JSON payload of already‑computed, verified facts about one MSME's loan eligibility assessment. "
            "Your only job is to turn those facts into the exact JSON output schema described below. You are a phrasing and synthesis layer, "
            "not a decision‑maker or a calculator – every number in your output must trace back to a number you were given.\n"
            "\n"
            "Return exactly this JSON shape (all fields required):\n"
            "{\n"
            "  \"executive_summary\": \"<2‑4 sentence paragraph, similar in role to a credit memo opening paragraph. Must state the eligibility score, the eligibility band, and one clear takeaway about the computed loan amount vs the requested amount.>\",\n"
            "  \"score_breakdown_narrative\": \"<1‑3 sentence paragraph walking through which of the 6 sub‑scores are strongest and weakest, referencing the actual sub‑score numbers given to you, and briefly noting the loan‑sizing basis (percentage of annual turnover).>\",\n"
            "  \"risk_summary\": \"<1‑2 sentence paragraph stating the overall risk level (low/moderate/high) and the single most important risk driver, grounded in the NPA/SMA/DPD facts given. If there are zero NPA/SMA and DPD is 0, this should be a clean, low‑risk statement.>\",\n"
            "  \"areas_of_improvement\": [\"<one specific, actionable recommendation per array item, each tied to a specific weak metric you were given. 2‑5 items. Each item should be one sentence, imperative mood (e.g. 'File all pending GST returns...'), suitable to display as a bullet point.>\"],\n"
            "  \"strengths\": [\"<one specific strength per array item, each tied to a specific strong metric you were given. 1‑4 items. If genuinely nothing is strong, return an empty array rather than inventing a strength.>\"]\n"
            "}\n"
        )

        # -------- User prompt -------------------------------------------------
        facts = {
            "business_name": msme_data.get('legal_name', 'The business'),
            "eligibility_score_out_of_100": eligibility_score,
            "eligibility_band": band,
            "eligibility_label": eligibility_label,
            "is_loan_eligible": is_eligible,
            "sub_scores_out_of_100": {
                sub_score_labels.get(k, k): v for k, v in sub_scores.items()
            },
            "computed_max_loan_amount_inr": computed_max_loan,
            "asking_amount_inr": asking_amount,
            "annual_revenue_inr": rev_meta.get('annual_revenue', 0),
            "revenue_yoy_growth_pct": rev_meta.get('yoy_growth_pct', 0),
            "gst_filing_pct_last_12mo": all_meta.get('gst_compliance', {}).get('filing_pct', 0),
            "itc_utilization_pct": all_meta.get('gst_compliance', {}).get('itc_ratio', 0),
            "credit_utilization_pct": all_meta.get('credit_util', {}).get('utilization_pct', 0),
            "max_days_past_due": rep_meta.get('max_dpd', 0),
            "npa_account_count": rep_meta.get('npa_count', 0),
            "sma_account_count": rep_meta.get('sma_count', 0),
            "business_vintage_years": all_meta.get('biz_stability', {}).get('vintage_years', 0),
        }
        user_prompt = (
            "Here are the verified, already‑computed facts for this MSME loan eligibility case. Do not recompute, "
            "re‑derive, or alter any of these numbers – only explain them. Produce your response as the single JSON object "
            "described in the system prompt, using only these facts:\n"
            + json.dumps(facts, indent=2)
        )
        return system_prompt, user_prompt

    async def _call_lm_studio(self, system_prompt: str, user_prompt: str) -> str:
        """Send the chat request to LM Studio and return the raw content string.

        Retries are performed for connection‑related errors only. HTTP 4xx/5xx responses are
        considered final – they raise ``LLMUnavailableError`` with the response body attached.
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "top_p": 0.9,
            "max_tokens": 900,
            "stream": False,
        }
        attempt = 0
        while True:
            attempt += 1
            start = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.post(f"{self.base_url}/chat/completions", json=payload)
                elapsed = time.perf_counter() - start
                logger.debug(
                    "LM Studio request payload size %d bytes, elapsed %.2f s, attempt %d",
                    len(json.dumps(payload).encode('utf-8')),
                    elapsed,
                    attempt,
                )
                if resp.status_code != 200:
                    raise LLMUnavailableError(
                        f"LM Studio returned HTTP {resp.status_code}: {resp.text}"
                    )
                try:
                    content = resp.json()["choices"][0]["message"]["content"]
                    return content
                except (KeyError, IndexError, json.JSONDecodeError) as e:
                    raise LLMResponseParseError(
                        f"Unexpected LM Studio response shape: {resp.text}"
                    ) from e
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                logger.warning(
                    "LM Studio call failed (%s) on attempt %d – retrying if possible",
                    type(e).__name__,
                    attempt,
                )
                if attempt > self.max_retries:
                    raise LLMUnavailableError('LM Studio unreachable after retries') from e
                await asyncio.sleep(0.2)

    def _parse_and_validate(self, raw_content: str) -> Dict[str, Any]:
        """Extract JSON, validate required keys/types, and perform light sanity checks.
        """
        text = raw_content.strip()
        if text.startswith('```json'):
            text = text[len('```json'):].strip()
            if text.endswith('```'):
                text = text[:-3].strip()
        # fallback to first/last braces
        if not (text.startswith('{') and text.endswith('}')):
            first = text.find('{')
            last = text.rfind('}')
            if first != -1 and last != -1 and first < last:
                text = text[first:last+1]
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMResponseParseError(
                f"Failed to parse LLM JSON (truncated to 500 chars): {text[:500]}"
            ) from e
        required_keys = [
            "executive_summary",
            "score_breakdown_narrative",
            "risk_summary",
            "areas_of_improvement",
            "strengths",
        ]
        missing = [k for k in required_keys if k not in data]
        if missing:
            raise LLMResponseParseError(f"Missing required keys in LLM output: {missing}")
        # basic type checks
        if not isinstance(data["executive_summary"], str) or not data["executive_summary"].strip():
            raise LLMResponseParseError("executive_summary must be a non‑empty string")
        if not isinstance(data["score_breakdown_narrative"], str) or not data["score_breakdown_narrative"].strip():
            raise LLMResponseParseError("score_breakdown_narrative must be a non‑empty string")
        if not isinstance(data["risk_summary"], str) or not data["risk_summary"].strip():
            raise LLMResponseParseError("risk_summary must be a non‑empty string")
        # lists or single strings for the arrays
        for key in ("areas_of_improvement", "strengths"):
            val = data[key]
            if isinstance(val, str):
                data[key] = [val]
            elif isinstance(val, list):
                if not all(isinstance(item, str) for item in val):
                    raise LLMResponseParseError(f"All items in {key} must be strings")
            else:
                raise LLMResponseParseError(f"{key} must be a list of strings or a single string")
        # length sanity for executive_summary
        exec_sum = data["executive_summary"].strip()
        if len(exec_sum) < 20 or len(exec_sum) > 3000:
            raise LLMResponseParseError(
                f"executive_summary length out of bounds ({len(exec_sum)} chars)"
            )
        # soft check for stray numbers – log warning only
        number_pattern = re.compile(r"₹?\d[\d,]*\.?\d*")
        # we don't have the original facts here, so we just log any number occurrences
        for field in ("executive_summary", "score_breakdown_narrative", "risk_summary"):
            for num in number_pattern.findall(data[field]):
                logger.warning(
                    "LLM output contains number %s in field %s that may not be grounded in facts", num, field
                )
        return data


# Singleton instance used by the rest of the application
llm_explainer_service = LLMExplainerService()
