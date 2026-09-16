import time
import os
import secrets
from dotenv import load_dotenv
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends

from fastapi import FastAPI, HTTPException
from app.email_processor import clean_email_body
from app.schemas import ThreadRequest, SummarizeResponse
from app.summarizer import summarize_with_ollama
from app.validation import validate_summary

load_dotenv()

API_KEY = os.getenv("AI_API_KEY")

if not API_KEY:
    raise RuntimeError("AI_API_KEY is not configured")

security = HTTPBearer()

app = FastAPI(
    title="Email AI Summarization API",
    version="1.0.0-demo",
    description=(
        "Self-hosted AI service for summarizing email threads. "
        "The API cleans email content, analyzes the thread using "
        "a self-hosted language model, validates the generated "
        "summary, and returns structured JSON for client applications."
    ),
)


API_MODEL_VERSION = "client-email-ai-v1"

async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if not secrets.compare_digest(
        credentials.credentials,
        API_KEY,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )

    return credentials.credentials

@app.get(
    "/health",
    summary="Health check",
)
async def health():
    return {
        "status": "ok",
        "model": API_MODEL_VERSION,
    }


@app.post(
    "/v1/email/summarize",
    dependencies=[Depends(verify_api_key)],
    response_model=SummarizeResponse,
    summary="Summarize an email thread",
    description=(
        "Accepts an ordered email thread and returns a structured "
        "AI-generated summary including key points, decisions, "
        "pending actions, and unresolved questions."
    ),
openapi_extra={
    "requestBody": {
        "content": {
            "application/json": {
                "example": {
                    "thread_id": "delivery-001",
                    "emails": [
                        {
                            "sender": "customer@example.com",
                            "recipients": [
                                "supplier@example.com"
                            ],
                            "subject": "Order 456 delivery",
                            "date": "2026-09-16T09:00:00",
                            "body": (
                                "Could you please confirm the status "
                                "of order 456? We have not received it yet."
                            ),
                        },
                        {
                            "sender": "supplier@example.com",
                            "recipients": [
                                "customer@example.com"
                            ],
                            "subject": "Re: Order 456 delivery",
                            "date": "2026-09-16T09:30:00",
                            "body": (
                                "The shipment was delayed because of a "
                                "transport issue. The revised expected "
                                "delivery date is September 20, 2026."
                            ),
                        },
                    ],
                }
            }
        }
    },
    "responses": {
        "200": {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "thread_id": "delivery-001",
                        "model": "client-email-ai-v1",
                        "latency_ms": 34751.83,
                        "model_latency_ms": 34750.83,
                        "summary": {
                            "overview": (
                                "Order 456 was delayed due to a "
                                "transport issue and the supplier "
                                "provided a revised delivery date."
                            ),
                            "key_points": [
                                "Order 456 delivery was delayed.",
                                "The revised expected delivery date "
                                "is September 20, 2026.",
                                "Customer acknowledged the update."
                            ],
                            "decisions": [
                                "The revised delivery date is "
                                "September 20, 2026."
                            ],
                            "action_items": [
                                {
                                    "owner": "supplier@example.com",
                                    "action": "Deliver order 456",
                                    "status": "pending",
                                    "deadline": "2026-09-20"
                                }
                            ],
                            "pending_questions": []
                        }
                    }
                }
            }
        },
        "422": {
            "description": "Validation error"
        },
        "502": {
            "description": "AI model service unavailable"
        }
    }
}
)

async def summarize_thread(request: ThreadRequest):
    start_time = time.perf_counter()

    if not request.emails:
        raise HTTPException(
            status_code=400,
            detail="Email thread cannot be empty.",
        )

    # 1. Clean incoming emails
    cleaned_emails = []

    for email in request.emails:
        cleaned_emails.append(
            {
                "sender": email.sender,
                "recipients": email.recipients,
                "date": email.date,
                "subject": email.subject,
                "body": clean_email_body(email.body),
            }
        )

    # 2. Build cleaned thread text
    thread_parts = []

    for index, email in enumerate(cleaned_emails, start=1):
        thread_parts.append(
            f"""
EMAIL {index}
From: {email["sender"]}
To: {", ".join(email["recipients"])}
Date: {email["date"]}
Subject: {email["subject"]}

{email["body"]}
""".strip()
        )

    thread_text = "\n\n".join(thread_parts)

    # 3. AI summarization
    try:
        model_start = time.perf_counter()

        summary, model_metrics = await summarize_with_ollama(
            thread_text
        )

        model_latency_ms = round(
            (time.perf_counter() - model_start) * 1000,
            2,
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    # 4. Deterministic validation
    summary = validate_summary(
        summary,
        [
            email["body"]
            for email in cleaned_emails
        ],
    )

    # 5. Total API latency
    latency_ms = round(
        (time.perf_counter() - start_time) * 1000,
        2,
    )

    return {
        "thread_id": request.thread_id,
        "model": API_MODEL_VERSION,
        "latency_ms": latency_ms,
        "model_latency_ms": model_latency_ms,
        "summary": summary.model_dump(),
    }
