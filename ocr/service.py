import json
import ollama


PARSE_PROMPT = """You are an invoice parser. Given a list of text blocks extracted from an invoice image (each with text content and position on page), identify what each block represents and return structured JSON.

Text blocks (each has: text, x, y, width, height as fractions of page 0.0-1.0):
{blocks}

Return ONLY valid JSON in this exact format:
{{
  "fields": {{
    "company_name": "...",
    "company_gstin": "...",
    "invoice_number": "...",
    "invoice_date": "...",
    "buyer_name": "...",
    "buyer_gstin": "...",
    "buyer_address": "...",
    "grand_total": "..."
  }},
  "elements": [
    {{
      "type": "text|field",
      "x_frac": 0.0,
      "y_frac": 0.0,
      "w_frac": 0.2,
      "h_frac": 0.03,
      "props": {{
        "content": "...",
        "field": "invoice_number|buyer_name|invoice_date|buyer_gstin|grand_total|company_name|null",
        "fontSize": 10,
        "fontWeight": "normal|bold",
        "textAlign": "left|center|right",
        "color": "#141413",
        "backgroundColor": "transparent"
      }}
    }}
  ]
}}

Rules:
- Use type "field" when the block is dynamic invoice data (invoice number, date, buyer info, totals)
- Use type "text" for static labels and headings
- x_frac/y_frac/w_frac/h_frac are fractions of page dimensions (0.0 to 1.0)
- Set field to null for static text elements
- Detect heading rows (bold, centred) and set fontWeight "bold"
"""


def parse_invoice_blocks(text_blocks: list, page_width: int, page_height: int) -> dict:
    """Send Tesseract blocks to Ollama for field mapping."""
    # Normalise positions to fractions
    normalised = []
    for b in text_blocks:
        normalised.append({
            'text': b['text'],
            'x_frac': round(b['x'] / page_width, 3),
            'y_frac': round(b['y'] / page_height, 3),
            'w_frac': round(b['width'] / page_width, 3),
            'h_frac': round(b['height'] / page_height, 3),
            'confidence': b.get('confidence', 0),
        })

    # Filter low-confidence blocks
    normalised = [b for b in normalised if b['confidence'] > 40]

    prompt = PARSE_PROMPT.format(blocks=json.dumps(normalised, indent=2))

    response = ollama.chat(
        model='llama3.1:8b',
        messages=[{'role': 'user', 'content': prompt}],
        options={'temperature': 0.1},
    )

    raw = response['message']['content'].strip()
    # Extract JSON from response (LLM may wrap in markdown)
    if '```' in raw:
        raw = raw.split('```')[1]
        if raw.startswith('json'):
            raw = raw[4:]

    parsed = json.loads(raw)

    # Convert fractional positions to px (A4 at 96dpi = 794×1123)
    A4_W, A4_H = 794, 1123
    for elem in parsed.get('elements', []):
        elem['x'] = round(elem.pop('x_frac') * A4_W)
        elem['y'] = round(elem.pop('y_frac') * A4_H)
        elem['width'] = max(40, round(elem.pop('w_frac') * A4_W))
        elem['height'] = max(14, round(elem.pop('h_frac') * A4_H))
        elem['id'] = f"ocr-{elem['x']}-{elem['y']}"
        elem['zIndex'] = 1

    return parsed
