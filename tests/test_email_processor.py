from app.email_processor import clean_email_body


sample = """
<div>Hello Amit,</div>

<div>Please check the invoice.</div>

<p>Thanks,<br>Raj</p>

<br>

On Sep 15, 2026, Amit wrote:
> Previous message
> Please check the invoice.

<div>--------------------</div>

Sent from my iPhone
"""


print("BEFORE:")
print(sample)

print("\nAFTER:")
print(clean_email_body(sample))
