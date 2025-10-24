from fastapi import APIRouter, Header, HTTPException
from typing import List
from models.schemas import QuestionResponse
from services.auth import verify_api_key
from bson import ObjectId
from models.schemas import product_questions,ShopifyProduct

router = APIRouter()
@router.get('/questions', response_model=List[QuestionResponse])
async def get_product_questions(product_id:str,x_api_key:str=Header(...,alias='X-API-KEY')):
    try:
        verify_api_key(x_api_key)
        print('product0d',product_id)
        product_obj = ShopifyProduct.objects.get(_id=product_id)
        pipeline = [
        {
            "$match" : {
                "category_id" : product_obj.category_id.id
            }
        },
        {
            "$project" : {
                "_id" : 0,
                "id" : {"$toString" : "$_id"},
                "question" : 1
            }
        },
        # {"$limit" : 6}
    ]
        product_questions_list = list(product_questions.objects.aggregate(*(pipeline)))
        return product_questions_list
    except Exception as e:
        print(f"error123: {e}")
        raise HTTPException(status_code=500,detail=str(e))
    