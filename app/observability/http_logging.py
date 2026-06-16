import json
import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import Response
from starlette.responses import StreamingResponse


logger = logging.getLogger("app.http")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


def add_http_logging_middleware(app: FastAPI) -> None:
    request_seq = 0
    max_body_chars = 3000

    def _decode_body(raw: bytes) -> str:
        if not raw:
            return ""
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return str(raw)

    def _truncate(text: str) -> str:
        if len(text) <= max_body_chars:
            return text
        return f"{text[:max_body_chars]} ...(truncated {len(text) - max_body_chars} chars)"

    def _format_payload(raw: bytes, content_type: str) -> str:
        text = _decode_body(raw)
        if not text:
            return "<empty>"

        if "application/json" in content_type.lower():
            try:
                parsed = json.loads(text)
                text = json.dumps(parsed, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                pass
        return _truncate(text)

    @app.middleware("http")
    async def log_request_response(request: Request, call_next):
        nonlocal request_seq
        request_seq += 1
        started_at = time.perf_counter()
        rid = request_seq

        logger.info("===== HTTP %s BEGIN =====", rid)
        logger.info(
            "[REQ ] id=%s method=%s path=%s",
            rid,
            request.method,
            request.url.path,
        )
        if request.url.query:
            logger.info("[REQ ] id=%s query=%s", rid, request.url.query)

        request_body = await request.body()
        if request_body:
            content_type = request.headers.get("content-type", "")
            logger.info(
                "[REQ ] id=%s body:\n%s",
                rid,
                _format_payload(request_body, content_type),
            )
        else:
            logger.info("[REQ ] id=%s body: <empty>", rid)

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            logger.exception(
                "[ERR ] id=%s unhandled_error elapsed_ms=%.2f",
                rid,
                elapsed_ms,
            )
            logger.info("===== HTTP %s END =====", rid)
            raise

        content_type = (response.headers.get("content-type") or "").lower()
        is_streaming = isinstance(response, StreamingResponse) or "text/event-stream" in content_type
        if is_streaming:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            level = logging.ERROR if response.status_code >= 500 else logging.INFO
            logger.log(
                level,
                "[RESP] id=%s status=%s elapsed_ms=%.2f body=<streaming omitted>",
                rid,
                response.status_code,
                elapsed_ms,
            )
            logger.info("===== HTTP %s END =====", rid)
            return response

        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        elapsed_ms = (time.perf_counter() - started_at) * 1000
        level = logging.ERROR if response.status_code >= 500 else logging.INFO
        resp_content_type = response.headers.get("content-type", "")
        logger.log(
            level,
            "[RESP] id=%s status=%s elapsed_ms=%.2f body:\n%s",
            rid,
            response.status_code,
            elapsed_ms,
            _format_payload(response_body, resp_content_type),
        )
        logger.info("===== HTTP %s END =====", rid)
        

        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
