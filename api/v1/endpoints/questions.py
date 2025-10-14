from fastapi import APIRouter, Header, HTTPException
from typing import List
from models.schemas import QuestionResponse
from services.auth import verify_api_key
from bson import ObjectId
from models.schemas import product_questions

router = APIRouter()
@router.get('/questions/{product_id}', response_model=List[QuestionResponse])
async def get_product_questions(product_id:str,x_api_key:str=Header(...,alias='X-API-KEY')):
    try:
        verify_api_key(x_api_key)
        questions=product_questions.object(product_id=ObjectId(product_id)).limit(5)
        return [QuestionResponse(id=str(q.id),question=q.question) for q in questions]
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    