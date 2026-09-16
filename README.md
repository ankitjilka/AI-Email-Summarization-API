# AI Email Summarization API

Self-hosted AI backend for summarizing email threads from a Gmail-like application.

This POC accepts an email thread through an API and returns a structured summary containing:

- Overview
- Key points
- Decisions
- Pending action items
- Pending questions

> The Gmail-like UI is **not part of this project**. The client application can call this API from its existing **AI Summary** feature.

---

## Architecture

```text
Client Gmail-like Application
            |
            | POST /v1/email/summarize
            | Authorization: Bearer <API_KEY>
            v
        FastAPI API
            |
            v
    Email Preprocessing
            |
            v
       Qwen3-4B
        via Ollama
            |
            v
   Structured JSON Output
            |
            v
   Validation / Normalization
            |
            v
       API Response
```

---

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python |
| API | FastAPI |
| LLM Runtime | Ollama |
| Current Model | Qwen3-4B |
| Validation | Pydantic + Python |
| Email Processing | Custom Python preprocessing |
| API Documentation | OpenAPI / Swagger |
| Authentication | Bearer API Key |

> **vLLM is not used in the current POC.** It can be considered later for GPU-based production inference.

---

## Why Qwen3-4B?

For this POC, **Qwen3-4B** was selected based on the available development hardware and the need to balance summary quality with inference latency.

The development machine is CPU-only:

- Intel Core i5-12450H
- 14 GB RAM
- Intel integrated graphics
- No NVIDIA GPU

Qwen3-8B was initially tested and produced good summaries, but inference on the CPU was significantly slower for multi-email threads.

Qwen3-4B was then evaluated using the same email-thread scenarios and provided a better speed/quality balance for the POC.

Therefore:

```text
Qwen3-8B
    ↓
Higher resource requirement / slower CPU inference

Qwen3-4B
    ↓
Good summarization quality
+
Lower resource requirement
+
Better POC response time
```

---

## Features

- Summarizes complete email threads
- Understands chronological conversation state
- Extracts key points
- Extracts decisions
- Identifies pending actions
- Identifies unresolved questions
- Handles common HTML / quoted-reply / signature noise
- Returns structured JSON
- Validates model output before returning it
- API protected with Bearer authentication
- API latency metrics included in the response

---

# API

## 1. Health Check

```http
GET /health
```

Example response:

```json
{
  "status": "ok",
  "model": "client-email-ai-v1"
}
```

---

## 2. Summarize Email Thread

```http
POST /v1/email/summarize
```

### Authentication

```http
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

### Request

```json
{
  "thread_id": "delivery-001",
  "emails": [
    {
      "sender": "customer@example.com",
      "recipients": [
        "supplier@example.com"
      ],
      "subject": "Order 456 delivery",
      "date": "2026-09-16T09:00:00",
      "body": "Could you please confirm the status of order 456? We have not received it yet."
    },
    {
      "sender": "supplier@example.com",
      "recipients": [
        "customer@example.com"
      ],
      "subject": "Re: Order 456 delivery",
      "date": "2026-09-16T09:30:00",
      "body": "The shipment was delayed because of a transport issue. The revised expected delivery date is September 20, 2026."
    }
  ]
}
```

### Response

```json
{
  "thread_id": "delivery-001",
  "model": "client-email-ai-v1",
  "latency_ms": 34751.83,
  "model_latency_ms": 34750.83,
  "summary": {
    "overview": "Order 456 was delayed and the supplier provided a revised delivery date.",
    "key_points": [
      "Order 456 delivery was delayed.",
      "The revised expected delivery date is September 20, 2026."
    ],
    "decisions": [
      "The revised delivery date is September 20, 2026."
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
```

---

## Response Structure

| Field | Description |
|---|---|
| `thread_id` | Original thread identifier |
| `model` | API-level model/version identifier |
| `latency_ms` | Total API processing time |
| `model_latency_ms` | Model inference time |
| `summary.overview` | Concise thread summary |
| `summary.key_points` | Important facts from the conversation |
| `summary.decisions` | Confirmed decisions or outcomes |
| `summary.action_items` | Actions still pending at the end of the thread |
| `action_items.owner` | Responsible person/team when identifiable |
| `action_items.action` | Pending action |
| `action_items.status` | Current status |
| `action_items.deadline` | Explicit calendar date in `YYYY-MM-DD` format, otherwise `null` |
| `summary.pending_questions` | Unresolved questions |

---

# AI Processing

The API processes the email thread in several stages:

```text
Raw Email Thread
       |
       v
Email Preprocessing
       |
       v
Qwen3-4B
       |
       v
Structured JSON
       |
       v
Validation / Normalization
       |
       v
Final API Response
```

### Email preprocessing

The current preprocessing layer handles common email noise such as:

- HTML formatting
- Quoted replies
- Common signatures
- Extra whitespace and formatting

### Validation

The AI output is validated after generation.

Examples:

- Requests are not treated as approvals.
- Completed actions are not returned as pending actions.
- Future commitments can become pending action items.
- Explicit dates are normalized.
- Relative terms such as `today`, `tomorrow`, `soon`, and `shortly` are not automatically converted into calendar dates.

---

# Authentication

The summarization endpoint requires a Bearer API key.

Example:

```http
Authorization: Bearer <API_KEY>
```

### Invalid key

```json
{
  "detail": "Invalid API key"
}
```

### Missing authentication

The API rejects unauthenticated requests.

> For production, the API key should be stored using secure secret management and the API should be served over HTTPS.

---

# Error Responses

| HTTP Status | Meaning |
|---|---|
| `400` | Invalid request |
| `401` | Invalid API key |
| `403` | Authentication missing |
| `422` | Request validation error |
| `502` | AI/model service unavailable |

---

# Swagger / OpenAPI

After starting the API:

```text
http://127.0.0.1:8000/docs
```

Swagger provides:

- API endpoint documentation
- Request schema
- Response schema
- Authentication
- Example payloads
- Interactive API testing

---

# Local Setup

## 1. Clone the repository

```bash
git clone <repository-url>
cd AI-Email-Summarization-API
```

## 2. Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Install / start Ollama

Make sure Ollama is installed and running.

Pull the model:

```bash
ollama pull qwen3:4b
```

## 5. Configure environment

Create `.env`:

```env
AI_API_KEY=replace-with-your-api-key
```

## 6. Start API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

---

# Project Structure

```text
email-ai/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── schemas.py
│   ├── summarizer.py
│   ├── email_processor.py
│   └── validation.py
│
├── tests/
│   ├── evaluation/
│   │   ├── 01_invoice.json
│   │   ├── 02_meeting.json
│   │   ├── 03_complaint.json
│   │   ├── 04_delivery.json
│   │   └── 05_negotiation.json
    ├── run_evaluation.py
│   └── test_email_processor.py
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

# POC Evaluation

The current POC was tested using multiple email scenarios:

| Scenario | Purpose |
|---|---|
| Invoice | Quantity mismatch and task state |
| Meeting | Schedule changes and confirmation |
| Complaint | Completed vs pending actions |
| Delivery | Future commitment and explicit deadline |
| Negotiation | Request vs offer vs approval |

The current local CPU-only setup generally produces summaries in the tens-of-seconds range for small threads.

> Production latency should be benchmarked separately on the target production hardware and expected workload.

---

## Run Evaluation Scenarios

The repository includes 5 representative email-thread test scenarios:

- Invoice
- Meeting
- Customer Complaint
- Delivery
- Pricing Negotiation

Make sure the API is running first:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000

```
Open another terminal.
Set the API key:
```bash
export AI_API_KEY="YOUR_REAL_API_KEY"

```

Then:
```bash
source .venv/bin/activate
python tests/run_evaluation.py
```

It will automatically run:
```bash
01_invoice.json
02_meeting.json
03_complaint.json
04_delivery.json
05_negotiation.json
```
and print the response for each.


---

# Integration

The client application only needs to call:

```http
POST /v1/email/summarize
```

Example JavaScript:

```javascript
const response = await fetch(
  "https://<AI-SERVICE-HOST>/v1/email/summarize",
  {
    method: "POST",
    headers: {
      "Authorization": "Bearer <API_KEY>",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      thread_id: "thread-123",
      emails: [...]
    })
  }
);

const data = await response.json();

console.log(data.summary.overview);
console.log(data.summary.key_points);
console.log(data.summary.decisions);
console.log(data.summary.action_items);
console.log(data.summary.pending_questions);
```

> The client application should call the AI API rather than calling Ollama directly. This keeps the UI independent of the underlying AI model/runtime.

---

# Current POC vs Production

| Area | Current POC | Future Production |
|---|---|---|
| Model | Qwen3-4B | Evaluate larger/fine-tuned model |
| Runtime | Ollama | GPU inference runtime such as vLLM can be evaluated |
| Hardware | Local CPU | GPU-capable server |
| API | FastAPI | Scaled production API |
| Authentication | Bearer API key | Production secret/access management |
| Evaluation | Small test dataset | Larger regression/evaluation dataset |
| Training | Not included | Controlled fine-tuning using approved client data |
| UI | Not included | Existing client application integrates API |

---

# Future AI Improvement

The current POC does **not** automatically train on every email.

A controlled improvement workflow can be:

```text
Email Thread
     |
     v
AI Summary
     |
     v
Human Approval / Correction
     |
     v
Curated Dataset
     |
     v
Evaluation
     |
     v
Fine-tuning / Model Adaptation
     |
     v
New Model Version
```

This allows the system to become more tailored to the client's requirements over time while keeping training data controlled.

---

# Important Notes

- The current POC uses a self-hosted open-weight model.
- No third-party LLM API is required for the current demo.
- The current demo does **not** train an LLM from scratch.
- vLLM is **not** used in the current POC.
- Real production deployment should use HTTPS, secure secret management, logging/monitoring, rate limiting, and appropriate data-retention controls.
- Real customer emails should not be committed to this repository.

---

## Demo Status

**Current POC capabilities:**

- ✅ Self-hosted AI inference
- ✅ Email thread summarization
- ✅ Structured JSON API
- ✅ Email preprocessing
- ✅ Validation / normalization
- ✅ API authentication
- ✅ Swagger/OpenAPI
- ✅ Multiple evaluation scenarios
- ✅ Ready for integration testing by client developers