from models.schemas import product,product_questions

from openai import OpenAI
from openai import OpenAIError
from openai.types.chat import ChatCompletionMessage
from fastapi import HTTPException
from bson import ObjectId
import math
import os
from dotenv import load_dotenv
load_dotenv() 
def productDetails(product_id):
    product_id = product.objects.get(id=product_id)
    pipeline =[
        {
            "$match" : {
                "_id" : (product_id.id),
            }
        },
        {
                "$lookup": {
                    "from": "product_category",
                    "localField": "category_id",
                    "foreignField": "_id",
                    "as": "product_category_ins"
                }
            },
            {"$unwind" : "$product_category_ins"},
         {
            "$lookup": {
                "from": "brand",
                "localField": "brand_id",
                "foreignField": "_id",
                "as": "brand_ins"
            }
        },
        {
        "$unwind": {
            "path": "$brand_ins", 
            "preserveNullAndEmptyArrays": True
        }
        },
        {
           "$project" :{
            "_id":0,
            "id" : {"$toString" : "$_id"},
            "product_name" : {"$ifNull": ["$product_name", "N/A"]},
            "sku_number_product_code_item_number" : {"$ifNull": ["$sku_number_product_code_item_number", "N/A"]},
            "model" : {"$ifNull": ["$model", "N/A"]},
            "mpn" : {"$ifNull": ["$mpn", "N/A"]},
            "upc_ean" : {"$ifNull": ["$upc_ean", "N/A"]},
            "logo" : {"$ifNull" : [{"$first":"$images"},"http://example.com/"]},
            "long_description" : {"$ifNull": ["$long_description", "N/A"]},
            "short_description" : {"$ifNull": ["$short_description", "N/A"]},
            "list_price" : {"$ifNull": ["$list_price", 0.0]},
            "msrp" : {"$ifNull" : ["$msrp",0.0]},
            "was_price" : {"$ifNull" : ["$was_price",0.0]},
            "discount": { 
            "$concat": [
                { "$toString": { "$round": [{"$ifNull": ["$discount", 0]}, 2] } }, 
                "%" 
            ] 
            },
            "brand_name" : {"$ifNull": ["$brand_name", "N/A"]},
            "brand_logo" : {"$ifNull" : ["$brand_ins.logo",""]},
            "currency" : {"$ifNull": ["$currency", "N/A"]},
            "quantity" : {"$ifNull": ["$quantity", 0]},
            "availability" : {"$ifNull": ["$availability", False]},
            "images" : {"$ifNull": ["$images", []]},
            "attributes" : {"$ifNull": ["$attributes", {}]},
            "features" : {"$ifNull": ["$features", []]},
            "from_the_manufacture" : {"$ifNull": ["$from_the_manufacture", "N/A"]},
            "visible" : {"$ifNull": ["$visible", False]},
            "end_level_category" : {"$ifNull": ["$product_category_ins.name", "N/A"]},
            "ai_generated_title" : {"$ifNull": ["$ai_generated_title", []]},
            "ai_generated_description" : {"$ifNull": ["$ai_generated_description", []]},
            "ai_generated_features" : {"$ifNull": ["$ai_generated_features", []]},
           }
        }
    ]
    product_list = list(product.objects.aggregate(*(pipeline)))
    def sanitize_floats(obj):
        if isinstance(obj, dict):
            return {k: sanitize_floats(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize_floats(i) for i in obj]
        elif isinstance(obj, float):
            return 0.0 if math.isnan(obj) or math.isinf(obj) else obj
        else:
            return obj

    product_list = list(product.objects.aggregate(*pipeline))
    if product_list:
        return sanitize_floats(product_list[0])
    else:
        return {}


# genai.configure(api_key="AIzaSyABnL_dU_kIQ0lRMyFy7BpgsdO5AK9DY6Q")  # techteam 
OPEN_AI_KEY = os.getenv("OPEN_AI_KEY")
client = OpenAI(api_key=OPEN_AI_KEY)

def get_product_assistant_response(user_query, product_id):
    products = productDetails(product_id)
    del products["ai_generated_description"]
    del products["ai_generated_title"]
    del products["ai_generated_features"]
    product_info = str(products)

    prompt = f"""
    You are an AI assistant for an e-commerce website. Your task is to provide clear and relevant answers based on the given product details.

    ### Instructions:
    1. Answer concisely based only on the product details provided.
    2. If the requested detail is missing, say: "Sorry, this information is not available for the product."
    3. Avoid raw data dumps—only provide direct human-readable responses.
    4. If the question is unrelated to the product, say: "I can only provide product-related information."

    ---

    ### Product Information:
    {product_info}

    ---

    ### User Query:
    {user_query}

    ### AI Response:
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful product assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except OpenAIError as e:
        return f"An error occurred: {str(e)}"

  
class ChatbotService:
    def __init__(self):
        pass
    async def process_chat_message(self,user_query:str,product_id:str,session_id:str=None):
        product=productDetails(product_id)
        if not product:
            raise HTTPException(status_code=404,detail='Product nnot found')
        exisiting_answer=product_questions.objects(question=user_query).first()
        if exisiting_answer and exisiting_answer.answer  and exisiting_answer.answer.answer.strip():
            return exisiting_answer.answer
        response_text=get_product_assistant_response(user_query,product_id)
        product_category_id=product.get('category_id')
        if isinstance(product_category_id,str):
            product_category_id=ObjectId(product_category_id)
        product_questions(question=user_query,answer=response_text,category_id=product_category_id,product_id=ObjectId(product_id)).save()
        return response_text