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

QUICK_INSIGHTS_PROMPT = """Based on the following business data snapshot for Umiya Chemical Trading, generate 3-4 quick actionable insights for the dashboard.

{data}

For each insight provide:
- A short title (max 8 words)
- A one-sentence summary with specific numbers
- Category: sales, inventory, customers, or operations
- Priority: info, warning, or critical

Return as a JSON array with keys: title, summary, category, priority.
Respond with ONLY the JSON array, no other text."""
