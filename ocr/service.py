import json
import ollama


PARSE_PROMPT = """Extract invoice fields from these text lines. Return ONLY a JSON object, no explanation, no code.

Text lines:
{lines}

Return this exact JSON structure:
{{
  "fields": {{
    "company_name": "",
    "company_gstin": "",
    "invoice_number": "",
    "invoice_date": "",
    "buyer_name": "",
    "buyer_gstin": "",
    "buyer_address": "",
    "grand_total": ""
  }}
}}

Fill in values found in the text. Leave empty string if not found."""


def parse_invoice_blocks(text_blocks: list, page_width: int, page_height: int) -> dict:
    """Send OCR text blocks to Ollama for field extraction."""
    # Group words into lines by y-coordinate (bucket to nearest 20px)
    line_bucket = {}
    for b in text_blocks:
        y_key = round(b['y'] / 20) * 20
        if y_key not in line_bucket:
            line_bucket[y_key] = []
        line_bucket[y_key].append(b['text'])

    # Build compact line list sorted by y position
    lines = []
    for y_key in sorted(line_bucket.keys()):
        line_text = ' '.join(line_bucket[y_key]).strip()
        if line_text:
            lines.append(line_text)

    # Keep at most 60 lines to stay well under token limit
    lines = lines[:60]
    lines_text = '\n'.join(lines)

    prompt = PARSE_PROMPT.format(lines=lines_text)

    response = ollama.chat(
        model='llama3.1:8b',
        messages=[{'role': 'user', 'content': prompt}],
        options={'temperature': 0.0, 'num_ctx': 2048},
    )

    raw = response['message']['content'].strip()

    # Extract JSON from markdown code fences if present
    if '```' in raw:
        parts = raw.split('```')
        raw = parts[1]
        if raw.startswith('json'):
            raw = raw[4:]
    raw = raw.strip()

    # Find the JSON object in the response
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1:
        raw = raw[start:end + 1]

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f'Ollama returned invalid JSON: {e}\nRaw (first 300): {raw[:300]}')

    # Return fields only (no element layout — OCR populates the invoice form, not the canvas)
    return {'fields': parsed.get('fields', {})}
