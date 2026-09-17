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
- If the thread is purely informational and contains no explicit
  request, commitment, assignment, scheduled activity, or unresolved
  question, return action_items as an empty list.

- Never infer an action merely because an email recipient might
  reasonably want to do something.

- Acknowledgements such as "Thanks", "Noted", "Received", or
  "Thanks for the information" do not create an action item.

- Do not create an action item from general information, announcements,
  notifications, or reminders unless an explicit action is requested
  or committed to.

- Never mark something as a decision unless the emails explicitly
  confirm, approve, accept, finalize, or agree to it.

- Words such as "requested", "proposed", "if approved",
  "would like", "might", "could", and "possible" do NOT indicate
  a confirmed decision.

- "I will check whether X is possible" means the feasibility check
  is pending. It does NOT mean X has been approved, scheduled, or confirmed.

- Do not confuse a date mentioned inside an action with the deadline
  for performing that action.

- Every future action, planned activity, scheduled event, or promised
  deliverable that has not yet happened must appear in action_items.

- If the latest email changes an earlier planned date, use the latest
  date and keep the related action as pending.

- A future date mentioned for an action indicates a deadline/target
  only when that action is still pending.

- Example:
  "The revised expected dispatch date is September 24, 2026."
  means:
  action = dispatch the order
  status = pending
  deadline = 2026-09-24

- If a later email says an action will happen after another action,
  keep both pending actions when both are still unfinished.


Example:
"I will check whether delivery on September 25 is possible."
→ action = check delivery feasibility
→ status = pending
→ deadline = null
→ delivery on September 25 is NOT confirmed.


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
                        "num_predict": 500,
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
