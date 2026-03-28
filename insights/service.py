import json
import logging
from datetime import datetime, timezone
from core import ollama_client
from insights.context import insight_context_service
from insights.prompts import (
    INSIGHT_SALES_PROMPT,
    INSIGHT_INVENTORY_PROMPT,
    INSIGHT_CUSTOMER_PROMPT,
    INSIGHT_REVENUE_PROMPT,
    INSIGHT_ANOMALY_PROMPT,
    QUICK_INSIGHTS_PROMPT,
)

logger = logging.getLogger(__name__)

INSIGHT_TITLES = {
    "sales_trend": "Sales Trend Analysis",
    "inventory_health": "Inventory Health Report",
    "customer_analysis": "Customer Analysis",
    "revenue_summary": "Revenue Summary",
    "anomaly_detection": "Anomaly Detection",
}

INSIGHT_PROMPTS = {
    "sales_trend": INSIGHT_SALES_PROMPT,
    "inventory_health": INSIGHT_INVENTORY_PROMPT,
    "customer_analysis": INSIGHT_CUSTOMER_PROMPT,
    "revenue_summary": INSIGHT_REVENUE_PROMPT,
    "anomaly_detection": INSIGHT_ANOMALY_PROMPT,
}


class InsightsService:
    """Generates AI-powered business insights."""

    async def generate_insight(self, insight_type: str, period_days: int = 30) -> dict:
        """Generate a specific type of insight."""
        # Get data from ERP
        data = insight_context_service.get_data_for_insight(insight_type, period_days)

        # Get the appropriate prompt
        prompt_template = INSIGHT_PROMPTS.get(insight_type)
        if not prompt_template:
            return {
                "insight_type": insight_type,
                "title": "Unknown Insight Type",
                "content": f"Insight type '{insight_type}' is not supported.",
                "data": None,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        prompt = prompt_template.format(data=data)

        try:
            content = await ollama_client.generate(prompt, temperature=0.4)
        except Exception as e:
            logger.error(f"Failed to generate insight: {e}")
            content = "Unable to generate insights at this time. Please ensure the AI model is running and try again."

        return {
            "insight_type": insight_type,
            "title": INSIGHT_TITLES.get(insight_type, "Insight"),
            "content": content,
            "data": None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def quick_insights(self) -> dict:
        """Generate quick dashboard insights."""
        data = insight_context_service.get_quick_insights_data()
        prompt = QUICK_INSIGHTS_PROMPT.format(data=data)

        try:
            raw = await ollama_client.generate(prompt, temperature=0.3)
            # Try to parse as JSON
            insights = self._parse_insights_json(raw)
        except Exception as e:
            logger.error(f"Failed to generate quick insights: {e}")
            insights = [
                {
                    "title": "AI Temporarily Unavailable",
                    "summary": "Could not generate insights. Please check that Ollama is running.",
                    "category": "operations",
                    "priority": "warning",
                }
            ]

        return {
            "insights": insights,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _parse_insights_json(raw: str) -> list[dict]:
        """Parse LLM response into structured insights."""
        # Try to find JSON array in the response
        raw = raw.strip()

        # Find the JSON array boundaries
        start = raw.find("[")
        end = raw.rfind("]")

        if start != -1 and end != -1:
            try:
                parsed = json.loads(raw[start:end + 1])
                if isinstance(parsed, list):
                    # Validate each insight has required fields
                    valid = []
                    for item in parsed:
                        if isinstance(item, dict) and "title" in item and "summary" in item:
                            valid.append({
                                "title": str(item.get("title", ""))[:60],
                                "summary": str(item.get("summary", ""))[:200],
                                "category": str(item.get("category", "operations")),
                                "priority": str(item.get("priority", "info")),
                            })
                    if valid:
                        return valid
            except json.JSONDecodeError:
                pass

        # Fallback: return the raw text as a single insight
        return [
            {
                "title": "Business Overview",
                "summary": raw[:200] if raw else "No insights available.",
                "category": "operations",
                "priority": "info",
            }
        ]


insights_service = InsightsService()
