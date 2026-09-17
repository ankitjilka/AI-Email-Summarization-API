import json
import os
import subprocess
from pathlib import Path


API_URL = "http://127.0.0.1:8000/v1/email/summarize"
API_KEY = os.environ["AI_API_KEY"]

TEST_DIR = Path(__file__).parent / "evaluation"

SCENARIOS = [
    "01_invoice.json",
    "02_meeting.json",
    "03_complaint.json",
    "04_delivery.json",
    "05_negotiation.json",
    "06_informational.json",
    "07_multiple_actions.json",
    "08_state_change.json",
    "09_relative_dates.json",
    "10_multiple_dates.json",
    "11_long_thread.json",
]


for filename in SCENARIOS:
    print("\n" + "=" * 70)
    print(f"Running: {filename}")
    print("=" * 70)

    path = TEST_DIR / filename

    result = subprocess.run(
        [
            "curl",
            "-s",
            "-X",
            "POST",
            API_URL,
            "-H",
            f"Authorization: Bearer {API_KEY}",
            "-H",
            "Content-Type: application/json",
            "--data",
            f"@{path}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    try:
        response = json.loads(result.stdout)
        print(json.dumps(response, indent=2))

        if "latency_ms" in response:
            print(
                f"\nAPI latency: {response['latency_ms']:.2f} ms"
            )

        if "model_latency_ms" in response:
            print(
                f"Model latency: {response['model_latency_ms']:.2f} ms"
            )

    except json.JSONDecodeError:
        print("Invalid API response:")
        print(result.stdout)

    if result.stderr:
        print("\nError:")
        print(result.stderr)
