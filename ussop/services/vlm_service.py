"""
VLM Service — Vision Language Model integration for Ussop.

Supports multiple backends via a single unified interface:
  - local:     Moondream2, InternVL2, Qwen2-VL, Phi-3.5-Vision, LLaVA, PaliGemma
  - anthropic: Claude 3.5 Haiku / Opus
  - openai:    GPT-4o / GPT-4o-mini
  - google:    Gemini 2.0 Flash
  - groq:      LLaVA via Groq inference
  - nim:       NVIDIA NIM (OpenAI-compatible endpoint)

Three public methods:
  describe_defect(image_path, detections)  → natural language defect description
  suggest_annotations(image_path)          → pre-label suggestions for annotation queue
  answer_query(question, context)          → natural language → structured answer

Backend is selected by settings.VLM_BACKEND.
API keys are read from settings (set in .env).
"""

from __future__ import annotations

import base64
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── path setup so bare imports work ──────────────────────────────────────────
_svc_dir = Path(__file__).parent
_ussop_dir = _svc_dir.parent
_project_root = _ussop_dir.parent
for _p in (_ussop_dir, _project_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from config.settings import settings


# ── prompts ───────────────────────────────────────────────────────────────────

_DESCRIBE_PROMPT = (
    "You are an industrial quality control AI. "
    "Describe this manufacturing defect in one or two sentences. "
    "Include defect type, estimated size, orientation if visible, "
    "and likely cause. Be concise and technical."
)

_ANNOTATE_PROMPT = (
    "You are an industrial quality control AI. "
    "Identify all visible defects in this image. "
    "For each defect return a JSON list with objects: "
    '{"class": "<defect_type>", "box": [x1, y1, x2, y2], "confidence": 0.0-1.0}. '
    "Return ONLY the JSON array, no other text."
)

_QUERY_PROMPT_TEMPLATE = (
    "You are an industrial quality control assistant. "
    "Answer the following question about inspection data based on the context provided.\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}\n\n"
    "Answer concisely."
)


# ══════════════════════════════════════════════════════════════════════════════
# Backend implementations
# ══════════════════════════════════════════════════════════════════════════════

def _image_to_base64(image_path: str) -> str:
    """Read image file and encode as base64 string."""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def _image_media_type(image_path: str) -> str:
    suffix = Path(image_path).suffix.lower()
    return {"jpg": "image/jpeg", ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg", ".png": "image/png",
            ".bmp": "image/bmp", ".webp": "image/webp"}.get(suffix, "image/jpeg")


# ── Local backend ─────────────────────────────────────────────────────────────

class _LocalBackend:
    """
    Runs a small VLM locally on CPU via HuggingFace transformers.

    Supported model names (settings.VLM_LOCAL_MODEL):
      moondream2     — vikhyatk/moondream2           (1.8B, ~3 GB RAM)
      internvl2      — OpenGVLab/InternVL2-2B         (2B,   ~4 GB RAM)
      qwen2vl        — Qwen/Qwen2-VL-2B-Instruct      (2B,   ~4 GB RAM)
      phi35vision    — microsoft/Phi-3.5-vision-instruct (4B, ~5 GB RAM)
      llava          — llava-hf/llava-1.5-7b-hf (GGUF) (7B q4, ~6 GB RAM)
      paligemma      — google/paligemma-3b-pt-224      (3B,   ~5 GB RAM)
    """

    _HF_IDS = {
        "moondream2":  "vikhyatk/moondream2",
        "internvl2":   "OpenGVLab/InternVL2-2B",
        "qwen2vl":     "Qwen/Qwen2-VL-2B-Instruct",
        "phi35vision": "microsoft/Phi-3.5-vision-instruct",
        "llava":       "llava-hf/llava-1.5-7b-hf",
        "paligemma":   "google/paligemma-3b-pt-224",
    }

    def __init__(self):
        self._model = None
        self._processor = None
        self._model_name = settings.VLM_LOCAL_MODEL
        self._loaded = False

    def _load(self):
        if self._loaded:
            return
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoProcessor, AutoTokenizer
            from PIL import Image as PILImage

            hf_id = self._HF_IDS.get(self._model_name)
            if not hf_id:
                raise ValueError(
                    f"Unknown local VLM model: '{self._model_name}'. "
                    f"Valid options: {list(self._HF_IDS.keys())}"
                )

            cache_dir = settings.MODELS_DIR / "vlm" / self._model_name

            # Moondream2 has its own API
            if self._model_name == "moondream2":
                self._model = AutoModelForCausalLM.from_pretrained(
                    hf_id,
                    trust_remote_code=True,
                    torch_dtype=torch.float32,
                    cache_dir=str(cache_dir),
                )
                self._processor = AutoTokenizer.from_pretrained(
                    hf_id,
                    trust_remote_code=True,
                    cache_dir=str(cache_dir),
                )
            else:
                self._processor = AutoProcessor.from_pretrained(
                    hf_id,
                    trust_remote_code=True,
                    cache_dir=str(cache_dir),
                )
                self._model = AutoModelForCausalLM.from_pretrained(
                    hf_id,
                    trust_remote_code=True,
                    torch_dtype=torch.float32,
                    low_cpu_mem_usage=True,
                    cache_dir=str(cache_dir),
                )

            self._model.eval()
            logger.info(f"[VLM] Loaded local model: {hf_id}")
            self._loaded = True

        except ImportError as e:
            raise ImportError(
                f"Local VLM requires 'transformers' and 'torch': pip install transformers torch. "
                f"Original error: {e}"
            )

    def query(self, image_path: str, prompt: str) -> str:
        self._load()
        from PIL import Image as PILImage
        import torch

        image = PILImage.open(image_path).convert("RGB")

        if self._model_name == "moondream2":
            enc = self._model.encode_image(image)
            return self._model.answer_question(enc, prompt, self._processor)

        # Generic transformers chat template path (InternVL2, Qwen2-VL, Phi3.5, LLaVA, PaliGemma)
        messages = [{"role": "user", "content": [
            {"type": "image"},
            {"type": "text", "text": prompt},
        ]}]
        text = self._processor.apply_chat_template(
            messages, add_generation_prompt=True
        )
        inputs = self._processor(
            text=text, images=image, return_tensors="pt"
        )
        with torch.no_grad():
            output_ids = self._model.generate(
                **inputs,
                max_new_tokens=settings.VLM_MAX_TOKENS,
                do_sample=False,
            )
        generated = output_ids[0][inputs["input_ids"].shape[1]:]
        return self._processor.decode(generated, skip_special_tokens=True).strip()


# ── Anthropic backend ─────────────────────────────────────────────────────────

class _AnthropicBackend:
    """
    Claude vision via Anthropic API.
    Recommended models: claude-haiku-4-5-20251001 (fast/cheap), claude-opus-4-6 (best)
    """

    def query(self, image_path: str, prompt: str) -> str:
        try:
            import anthropic
        except ImportError:
            raise ImportError("pip install anthropic")

        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not set in settings / .env")

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        b64 = _image_to_base64(image_path)
        media_type = _image_media_type(image_path)

        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=settings.VLM_MAX_TOKENS,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": b64,
                    }},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return msg.content[0].text.strip()


# ── OpenAI backend ────────────────────────────────────────────────────────────

class _OpenAIBackend:
    """GPT-4o / GPT-4o-mini via OpenAI API."""

    def query(self, image_path: str, prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("pip install openai")

        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in settings / .env")

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        b64 = _image_to_base64(image_path)
        media_type = _image_media_type(image_path)

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=settings.VLM_MAX_TOKENS,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {
                        "url": f"data:{media_type};base64,{b64}"
                    }},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return resp.choices[0].message.content.strip()


# ── Google Gemini backend ─────────────────────────────────────────────────────

class _GoogleBackend:
    """Gemini 2.0 Flash via Google Generative AI."""

    def query(self, image_path: str, prompt: str) -> str:
        try:
            import google.generativeai as genai
            from PIL import Image as PILImage
        except ImportError:
            raise ImportError("pip install google-generativeai pillow")

        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not set in settings / .env")

        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")
        image = PILImage.open(image_path).convert("RGB")
        resp = model.generate_content(
            [prompt, image],
            generation_config={"max_output_tokens": settings.VLM_MAX_TOKENS},
        )
        return resp.text.strip()


# ── Groq backend ──────────────────────────────────────────────────────────────

class _GroqBackend:
    """LLaVA via Groq ultra-fast inference."""

    def query(self, image_path: str, prompt: str) -> str:
        try:
            from groq import Groq
        except ImportError:
            raise ImportError("pip install groq")

        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set in settings / .env")

        client = Groq(api_key=settings.GROQ_API_KEY)
        b64 = _image_to_base64(image_path)
        media_type = _image_media_type(image_path)

        resp = client.chat.completions.create(
            model="llava-v1.5-7b-4096-preview",
            max_tokens=settings.VLM_MAX_TOKENS,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {
                        "url": f"data:{media_type};base64,{b64}"
                    }},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return resp.choices[0].message.content.strip()


# ── NVIDIA NIM backend ────────────────────────────────────────────────────────

class _NIMBackend:
    """
    NVIDIA NIM — OpenAI-compatible endpoint.
    Supports: phi-3-vision, llama-3.2-11b-vision, neva-22b, fuyu-8b
    """

    def query(self, image_path: str, prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("pip install openai")

        if not settings.NVIDIA_NIM_API_KEY:
            raise ValueError("NVIDIA_NIM_API_KEY not set in settings / .env")

        client = OpenAI(
            base_url=settings.NVIDIA_NIM_BASE_URL,
            api_key=settings.NVIDIA_NIM_API_KEY,
        )
        b64 = _image_to_base64(image_path)
        media_type = _image_media_type(image_path)

        resp = client.chat.completions.create(
            model=settings.NVIDIA_NIM_MODEL,
            max_tokens=settings.VLM_MAX_TOKENS,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {
                        "url": f"data:{media_type};base64,{b64}"
                    }},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return resp.choices[0].message.content.strip()


# ══════════════════════════════════════════════════════════════════════════════
# Public VLMService
# ══════════════════════════════════════════════════════════════════════════════

_BACKEND_MAP = {
    "local":     _LocalBackend,
    "anthropic": _AnthropicBackend,
    "openai":    _OpenAIBackend,
    "google":    _GoogleBackend,
    "groq":      _GroqBackend,
    "nim":       _NIMBackend,
}


class VLMService:
    """
    Unified VLM interface. Backend is chosen by settings.VLM_BACKEND.

    Usage:
        vlm = VLMService()
        desc = vlm.describe_defect("/path/to/crop.jpg", detection_dict)
        suggestions = vlm.suggest_annotations("/path/to/full_image.jpg")
        answer = vlm.answer_query("How many scratches today?", context_str)
    """

    def __init__(self):
        backend_cls = _BACKEND_MAP.get(settings.VLM_BACKEND)
        if backend_cls is None:
            raise ValueError(
                f"Unknown VLM_BACKEND: '{settings.VLM_BACKEND}'. "
                f"Valid: {list(_BACKEND_MAP.keys())}"
            )
        self._backend = backend_cls()
        logger.info(f"[VLM] Using backend: {settings.VLM_BACKEND}")

    # ── public API ────────────────────────────────────────────────────────────

    def describe_defect(
        self,
        image_path: str,
        detections: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Generate a natural language description of defects in the image.

        Args:
            image_path: Path to the original or cropped defect image.
            detections: Optional list of detection dicts (class_name, confidence, box)
                        — added to the prompt as context.

        Returns:
            Human-readable defect description, e.g.:
            "Linear surface crack ~12 mm, oriented 45°, likely thermal stress."
        """
        prompt = _DESCRIBE_PROMPT
        if detections:
            det_ctx = "; ".join(
                f"{d.get('class_name','unknown')} (conf {d.get('confidence',0):.2f})"
                for d in detections
            )
            prompt += f"\n\nDetected defects: {det_ctx}."

        return self._run(image_path, prompt, fallback="Description unavailable.")

    def suggest_annotations(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Ask the VLM to pre-label an image for the annotation queue.

        Returns:
            List of dicts: [{"class": "scratch", "box": [x1,y1,x2,y2], "confidence": 0.85}, ...]
            Empty list on failure or no detections.
        """
        raw = self._run(image_path, _ANNOTATE_PROMPT, fallback="[]")
        try:
            # Strip markdown fences if model returns ```json ... ```
            clean = raw.strip().strip("`")
            if clean.lower().startswith("json"):
                clean = clean[4:].strip()
            suggestions = json.loads(clean)
            if isinstance(suggestions, list):
                return suggestions
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"[VLM] Could not parse annotation JSON: {raw[:100]}")
        return []

    def answer_query(self, question: str, context: str = "") -> str:
        """
        Answer a natural language question about inspection data.

        Args:
            question: Operator's question, e.g. "How many scratches at Station 3 today?"
            context:  Stringified context (statistics, recent results) to ground the answer.

        Returns:
            Natural language answer string.
        """
        prompt = _QUERY_PROMPT_TEMPLATE.format(
            context=context or "No additional context provided.",
            question=question,
        )
        # answer_query doesn't use an image — pass a tiny placeholder path
        # handled gracefully: backends that require an image get a blank 1x1 PNG
        placeholder = self._ensure_placeholder()
        return self._run(placeholder, prompt, fallback="Unable to answer query.")

    # ── helpers ───────────────────────────────────────────────────────────────

    def _run(self, image_path: str, prompt: str, fallback: str = "") -> str:
        """Call backend with timeout and fallback handling."""
        start = time.monotonic()
        try:
            result = self._backend.query(image_path, prompt)
            elapsed = time.monotonic() - start
            logger.debug(f"[VLM] Response in {elapsed:.2f}s")
            return result
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.warning(f"[VLM] Backend error after {elapsed:.2f}s: {e}")
            if settings.VLM_FALLBACK_ON_ERROR:
                return fallback
            raise

    def _ensure_placeholder(self) -> str:
        """Create and cache a 1×1 white PNG for text-only queries."""
        placeholder = settings.DATA_DIR / "vlm_placeholder.png"
        if not placeholder.exists():
            try:
                from PIL import Image as PILImage
                PILImage.new("RGB", (1, 1), (255, 255, 255)).save(placeholder)
            except Exception:
                # If PIL not available, write raw PNG bytes
                _PNG_1X1 = (
                    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
                    b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
                    b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
                )
                placeholder.write_bytes(_PNG_1X1)
        return str(placeholder)

    def status(self) -> Dict[str, Any]:
        """Return current VLM configuration status."""
        backend = settings.VLM_BACKEND
        info: Dict[str, Any] = {
            "enabled": settings.VLM_ENABLED,
            "backend": backend,
        }
        if backend == "local":
            info["model"] = settings.VLM_LOCAL_MODEL
            info["loaded"] = getattr(self._backend, "_loaded", False)
        elif backend == "nim":
            info["nim_model"] = settings.NVIDIA_NIM_MODEL
            info["nim_base_url"] = settings.NVIDIA_NIM_BASE_URL
        return info


# ── Singleton ─────────────────────────────────────────────────────────────────

_vlm_service: Optional[VLMService] = None


def get_vlm_service() -> Optional[VLMService]:
    """
    Return the VLMService singleton if VLM_ENABLED, else None.
    Safe to call even when VLM is disabled — callers should check for None.
    """
    global _vlm_service
    if not settings.VLM_ENABLED:
        return None
    if _vlm_service is None:
        _vlm_service = VLMService()
    return _vlm_service
