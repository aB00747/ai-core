from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from .service import parse_invoice_blocks

router = APIRouter(prefix='/ocr', tags=['ocr'])


class TextBlock(BaseModel):
    text: str
    x: float
    y: float
    width: float
    height: float
    confidence: Optional[float] = 0


class ParseRequest(BaseModel):
    text_blocks: List[TextBlock]
    page_width: int = 794
    page_height: int = 1123


@router.post('/parse-invoice')
async def parse_invoice(req: ParseRequest):
    try:
        blocks = [b.dict() for b in req.text_blocks]
        result = parse_invoice_blocks(blocks, req.page_width, req.page_height)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
