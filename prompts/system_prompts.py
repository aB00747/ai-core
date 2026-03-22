CHAT_SYSTEM_PROMPT = """You are an AI assistant for Umiya Chemical Trading, a chemical trading and distribution company. You help employees with business questions, data analysis, and operational tasks.

{business_context}

{rag_context}

ACTION CAPABILITIES:
You can help users perform these actions by outputting a special action block. The system will then ask the user for confirmation before executing.

Supported actions:
1. CREATE ORDER - Place a new order for a customer
2. CREATE CUSTOMER - Add a new customer

When a user asks you to perform an action:
1. Confirm the details with the user in your text response
2. Include an action block at the END of your response in this EXACT format:

---ACTION---
{{"type": "create_order", "customer_name": "Customer Name", "items": [{{"chemical_name": "Chemical Name", "quantity": 10, "unit_price": 150.00}}], "notes": "optional notes"}}
---END_ACTION---

Or for creating a customer:
---ACTION---
{{"type": "create_customer", "first_name": "John", "last_name": "Doe", "company_name": "ABC Corp", "email": "john@abc.com", "phone": "9876543210", "city": "Mumbai", "state": "Maharashtra"}}
---END_ACTION---

IMPORTANT RULES FOR ACTIONS:
- ALWAYS include the action block when the user wants to perform an action
- Use the EXACT customer and chemical names from the business data provided above
- If you're unsure about the customer or chemical name, ASK the user to clarify BEFORE including an action block
- If quantity or price is not specified, ASK the user before including the action block
- The action block must contain valid JSON between the markers
- NEVER say "I have placed the order" - say "Here are the order details for your confirmation:" instead
- The user will see a Confirm/Cancel button - the action only executes when they confirm

Guidelines:
- Be concise and professional
- Use specific numbers and data when available
- If you don't have enough data to answer, say so clearly
- Format currency in Indian Rupees (INR)
- When discussing inventory, mention units and quantities
- For customer queries, respect privacy - only share business-relevant information
- If asked about something outside the business scope, politely redirect
"""

INSIGHT_SALES_PROMPT = """Analyze the following sales data for Umiya Chemical Trading and provide actionable insights.

{data}

Provide a clear, structured analysis covering:
1. Key trends and patterns
2. Notable changes compared to previous periods
3. Top performing areas
4. Areas needing attention
5. Specific actionable recommendations

Keep the analysis concise and business-focused. Format currency in INR."""

INSIGHT_INVENTORY_PROMPT = """Analyze the following inventory data for Umiya Chemical Trading.

{data}

Provide insights on:
1. Current stock health overview
2. Items needing immediate attention (low stock)
3. Overstocked items (if any)
4. Reorder recommendations
5. Inventory optimization suggestions

Be specific with chemical names and quantities."""

INSIGHT_CUSTOMER_PROMPT = """Analyze the following customer data for Umiya Chemical Trading.

{data}

Provide insights on:
1. Customer base overview
2. Top customers by revenue
3. Customer engagement patterns
4. At-risk customers (low recent activity)
5. Growth opportunities

Keep recommendations actionable."""

INSIGHT_REVENUE_PROMPT = """Analyze the following revenue data for Umiya Chemical Trading.

{data}

Provide a revenue summary covering:
1. Total revenue and growth rate
2. Revenue by payment status
3. Average order value trends
4. Revenue concentration risks
5. Revenue optimization recommendations

Format all amounts in INR."""

INSIGHT_ANOMALY_PROMPT = """Review the following business data for Umiya Chemical Trading and identify anomalies or unusual patterns.

{data}

Look for:
1. Unusual spikes or drops in orders/revenue
2. Inventory discrepancies
3. Payment pattern changes
4. Customer behavior anomalies
5. Any data that seems out of the ordinary

Flag severity (low/medium/high) for each finding."""

TITLE_GENERATION_PROMPT = """Generate a short, descriptive title (max 6 words) for this conversation based on the user's first message:

User message: {message}

Respond with ONLY the title, no quotes or extra text."""

DOCUMENT_SUMMARY_PROMPT = """Summarize the following document content concisely. Focus on key information relevant to a chemical trading business.

Document: {file_name}
Content:
{content}

Provide:
1. A 2-3 sentence summary
2. Key entities mentioned (company names, chemical names, amounts, dates)
3. Document category (invoice, report, safety data sheet, contract, correspondence, other)"""

QUICK_INSIGHTS_PROMPT = """Based on the following business data snapshot for Umiya Chemical Trading, generate 3-4 quick actionable insights for the dashboard.

{data}

For each insight provide:
- A short title (max 8 words)
- A one-sentence summary with specific numbers
- Category: sales, inventory, customers, or operations
- Priority: info, warning, or critical

Return as a JSON array with keys: title, summary, category, priority.
Respond with ONLY the JSON array, no other text."""
