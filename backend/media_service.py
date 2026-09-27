"""Voice transcription, image OCR/vision, and document text extraction — Sarvam AI only.

All AI processing goes through Sarvam AI (per user directive). No OpenAI / Anthropic / Gemini.

- Audio transcription: Sarvam Speech-to-Text (saaras:v3, auto-detect Hindi/English/Hinglish).
- Image OCR/vision: Sarvam Vision (Indic-first VLM).
- Document text: local extraction with pypdf / python-docx / openpyxl.
"""
import os
import io
import base64
import logging
import tempfile
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

SARVAM_API_KEY = os.environ["SARVAM_API_KEY"]
SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_VISION_URL = "https://api.sarvam.ai/v1/vision"

# Sarvam BCP-47 codes we accept from clients (everything else -> auto-detect).
_LANG_MAP = {
    "en": "en-IN", "en-in": "en-IN", "english": "en-IN",
    "hi": "hi-IN", "hi-in": "hi-IN", "hindi": "hi-IN",
    "bn": "bn-IN", "gu": "gu-IN", "kn": "kn-IN", "ml": "ml-IN",
    "mr": "mr-IN", "od": "od-IN", "pa": "pa-IN", "ta": "ta-IN",
    "te": "te-IN",
}


def _resolve_lang(language: str | None) -> str:
    """Return a Sarvam-compatible BCP-47 code, or 'unknown' for Hinglish/auto."""
    if not language:
        return "unknown"
    key = language.strip().lower()
    if key in ("auto", "unknown", "hinglish"):
        return "unknown"
    return _LANG_MAP.get(key, "unknown")


async def transcribe_audio(audio_bytes: bytes, filename: str, language: str = "auto") -> str:
    """Transcribe an audio clip via Sarvam STT. Auto-detects Hindi/English/Hinglish."""
    suffix = Path(filename).suffix.lower() or ".m4a"
    # Normalise to something Sarvam accepts.
    if suffix not in {".m4a", ".mp3", ".wav", ".webm", ".mp4", ".mpeg", ".mpga", ".aac", ".ogg", ".flac", ".opus", ".amr"}:
        suffix = ".m4a"
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_name = tmp.name

        lang = _resolve_lang(language)
        headers = {"api-subscription-key": SARVAM_API_KEY}

        with open(tmp_name, "rb") as fh:
            files = {"file": (Path(filename or "audio").name, fh, "application/octet-stream")}
            data = {"model": "saaras:v3", "language_code": lang, "with_timestamps": "false"}
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(SARVAM_STT_URL, headers=headers, data=data, files=files)

        if resp.status_code >= 400:
            logger.warning("Sarvam STT %s: %s", resp.status_code, resp.text[:200])
            resp.raise_for_status()
        payload = resp.json() if resp.content else {}
        text = payload.get("transcript") or payload.get("text") or ""
        return (text or "").strip()
    finally:
        if tmp_name:
            Path(tmp_name).unlink(missing_ok=True)


SARVAM_DOC_AI_JOB_URL = "https://api.sarvam.ai/doc-ai/v1/job/digitise"
SARVAM_DOC_AI_STATUS_URL = "https://api.sarvam.ai/doc-ai/v1/job/{job_id}/status"
SARVAM_DOC_AI_RESULTS_URL = "https://api.sarvam.ai/doc-ai/v1/job/{job_id}/results"


async def image_qa(image_bytes: bytes, mime_type: str, question: str) -> str:
    """OCR / document intelligence via Sarvam Document AI (Sarvam Vision 1.5,
    `doc-ai/v1/job/digitise` — async job + polling; the old /v1/vision endpoint
    was retired by the provider and returned 404). Understands English, Hindi
    and Hinglish documents."""
    headers = {"api-subscription-key": SARVAM_API_KEY}
    ext = "png" if "png" in (mime_type or "") else "jpg"
    async with httpx.AsyncClient(timeout=90) as client:
        # 1. Start the digitise job (multipart: file + options).
        resp = await client.post(
            SARVAM_DOC_AI_JOB_URL,
            headers=headers,
            files={"file": (f"upload.{ext}", image_bytes, mime_type or "image/jpeg")},
            data={"language": "en-IN", "output_format": "json", "model": "sarvam-vision-v1"},
        )
        if resp.status_code >= 400:
            logger.warning("Sarvam DocAI digitise %s: %s", resp.status_code, resp.text[:200])
            resp.raise_for_status()
        job = resp.json()
        job_id = job.get("job_id")
        if not job_id:
            return str(job)[:2000]

        # 2. Poll until a terminal status (completed / partially_completed / failed / rejected).
        status_payload: dict = {}
        for _ in range(20):  # up to ~40s
            st = await client.get(SARVAM_DOC_AI_STATUS_URL.format(job_id=job_id), headers=headers)
            if st.status_code < 400:
                status_payload = st.json() or {}
                state = str(status_payload.get("status", "")).lower()
                if state in ("completed", "partially_completed", "failed", "rejected"):
                    break
            await __import__("asyncio").sleep(2)

        # 3. Fetch the digitised output: documents[].pages[].blocks[].text
        #    sorted by reading_order (confirmed against the live API).
        doc_text = ""
        try:
            rres = await client.get(SARVAM_DOC_AI_RESULTS_URL.format(job_id=job_id), headers=headers)
            if rres.status_code < 400:
                rdata = rres.json() or {}
                lines: list[tuple[int, str]] = []
                for doc in rdata.get("documents") or []:
                    for page in doc.get("pages") or []:
                        for blk in page.get("blocks") or []:
                            txt = (blk.get("text") or "").strip()
                            if txt:
                                lines.append((int(blk.get("reading_order") or 0), txt))
                lines.sort(key=lambda x: x[0])
                doc_text = "\n".join(t for _, t in lines).strip()
                if not doc_text:
                    doc_text = str(rdata.get("output") or rdata.get("markdown") or "")[:4000]
        except Exception as e:  # noqa: BLE001
            logger.debug("DocAI results fetch failed: %s", e)
        if not doc_text and isinstance(status_payload, dict):
            out = status_payload.get("output") or status_payload.get("result") or ""
            if isinstance(out, str):
                doc_text = out[:4000]

        if not doc_text:
            state = str(status_payload.get("status", "unknown"))
            raise RuntimeError(f"Sarvam DocAI job did not complete (status={state})")

        # 4. Answer the caller's question over the extracted text using the text LLM
        #    (Document AI extracts; the question may ask for interpretation).
        q = (question or "").strip()
        if q and q.lower() not in ("ocr", "extract text", "read the text"):
            from ai_service import ai_chat
            answer = await ai_chat(
                [
                    {"role": "system", "content": "You analyze extracted document text (screenshots, invoices, receipts). Read numbers, dates and amounts exactly; never invent values. You understand English, Hindi and Hinglish."},
                    {"role": "user", "content": f"Document text:\n{doc_text[:6000]}\n\nQuestion: {q}"},
                ],
                temperature=0.3, max_tokens=900,
            )
            return answer
        return doc_text


def extract_document_text(data: bytes, filename: str, mime: str) -> str:
    """Best-effort text extraction from common document formats. Local only — no LLM."""
    ext = Path(filename).suffix.lower()
    try:
        if ext == ".pdf" or mime == "application/pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            return "\n".join((p.extract_text() or "") for p in reader.pages[:40]).strip()
        if ext in (".docx",):
            import docx
            d = docx.Document(io.BytesIO(data))
            return "\n".join(p.text for p in d.paragraphs).strip()
        if ext in (".xlsx",):
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            out = []
            for ws in wb.worksheets[:5]:
                out.append(f"# Sheet: {ws.title}")
                for row in ws.iter_rows(values_only=True):
                    cells = [str(c) for c in row if c is not None]
                    if cells:
                        out.append(" | ".join(cells))
            return "\n".join(out[:1000]).strip()
        if ext in (".csv", ".txt", ".md", ".json"):
            return data.decode("utf-8", errors="ignore")[:60000].strip()
    except Exception as e:
        logger.warning(f"Text extraction failed for {filename}: {e}")
    return ""
