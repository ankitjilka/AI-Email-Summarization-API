from pydantic import BaseModel, Field


class Email(BaseModel):
    sender: str = Field(
        ...,
        examples=["customer@example.com"],
    )

    recipients: list[str] = Field(
        default_factory=list,
        examples=[["support@example.com"]],
    )

    subject: str = Field(
        ...,
        examples=["Order 456 delivery"],
    )

    date: str = Field(
        ...,
        examples=["2026-09-16T09:30:00"],
    )

    body: str = Field(
        ...,
        examples=[
            "The shipment was delayed. "
            "The revised expected delivery date is September 20, 2026."
        ],
    )


class ThreadRequest(BaseModel):
    thread_id: str = Field(
        ...,
        examples=["delivery-001"],
    )

    emails: list[Email]


class ActionItem(BaseModel):
    owner: str
    action: str
    status: str
    deadline: str | None = None


class Summary(BaseModel):
    overview: str
    key_points: list[str]
    decisions: list[str]
    action_items: list[ActionItem]
    pending_questions: list[str]


class SummarizeResponse(BaseModel):
    thread_id: str
    model: str
    latency_ms: float
    model_latency_ms: float
    summary: Summary
