import httpx

from app.schemas import Summary


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

# Internal model. The client API should not depend on this name.
MODEL_NAME = "qwen3:4b"


def build_prompt(thread_text: str) -> str:
    return f"""
Summarize this email thread as structured JSON.

Rules:
- Use only facts explicitly stated in the emails.
- Analyze emails chronologically; the latest message determines current state.
- action_items = ONLY actions that are still pending at the end of the thread.
- Completed actions must NOT appear in action_items.
- Future commitments, scheduled activities, and promised deliveries MUST appear in action_items.
- Requests are not approvals.
- "I will check", "will send", "will deliver", "will arrange" are pending actions unless later completed.
- Use a deadline only when an explicit calendar date is stated.
- Do not convert today, tomorrow, soon, or shortly into a calendar date.
- Keep the summary concise.
- Return only JSON matching the provided schema.

Examples:
"Please correct the invoice" → pending action.
"Accounts has corrected the invoice" → completed, not an action item.
"We will deliver the order on September 20, 2026" → pending action with deadline 2026-09-20.
"I will check internally" → pending action.

EMAIL THREAD:
{thread_text}
"""

async def summarize_with_ollama(
    thread_text: str,
) -> tuple[Summary, dict]:

    schema = Summary.model_json_schema()

    prompt = build_prompt(thread_text)
   
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "stream": False,
                    "think": False,
                    "format": schema,
                    "options": {
                        "temperature": 0,
                        "num_predict": 300,
                    },
                },
            )

        response.raise_for_status()

        result = response.json()

        summary = Summary.model_validate_json(
    		result["response"]
	)

        metrics = {
    		"prompt_eval_count": result.get("prompt_eval_count"),
    		"prompt_eval_duration_ms": round(
        	result.get("prompt_eval_duration", 0) / 1_000_000,
        	2,
    	),
    	"eval_count": result.get("eval_count"),
    	"eval_duration_ms": round(
        	result.get("eval_duration", 0) / 1_000_000,
        	2,
    	),
    	"total_duration_ms": round(
        	result.get("total_duration", 0) / 1_000_000,
        	2,
    	),
       }

        return summary, metrics

    except httpx.HTTPError as exc:
        raise RuntimeError(
            f"Unable to communicate with Ollama: {exc}"
        ) from exc

    except (KeyError, ValueError, TypeError) as exc:
        raise RuntimeError(
            f"Invalid response received from Ollama: {exc}"
        ) from exc
