from fastapi import APIRouter, Depends
from dependencies import verify_api_key
from insights.schemas import InsightRequest, InsightResponse, QuickInsightsResponse
from insights.service import insights_service

router = APIRouter(prefix="/insights", tags=["Insights"], dependencies=[Depends(verify_api_key)])


@router.post("/generate/", response_model=InsightResponse)
async def generate_insight(request: InsightRequest):
    """Generate a specific business insight."""
    result = await insights_service.generate_insight(
        insight_type=request.insight_type,
        period_days=request.period_days,
    )
    return InsightResponse(**result)


@router.get("/quick/", response_model=QuickInsightsResponse)
async def quick_insights():
    """Generate quick dashboard insights."""
    result = await insights_service.quick_insights()
    return QuickInsightsResponse(**result)
