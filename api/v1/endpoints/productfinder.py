from fastapi import APIRouter, Header, HTTPException, Request,Query
from typing import List
from models.schemas import product_category, QuestionResponse, ShopifyProduct,filter
from services.auth import verify_api_key
from bson import ObjectId
import pandas as pd
from spellchecker import SpellChecker
router = APIRouter()
@router.get('/fourth_level_categories')
async def fourth_level_categories_view(x_api_key: str = Header(..., alias='X-API-KEY')):
    try:
        verify_api_key(x_api_key)
        categories_cursor = product_category.objects(end_level=True)
        categories_list = []
        for ins in categories_cursor:
            cat = {
                "id": str(ins.id),
                "name": ins.name,
            }
            categories_list.append(cat)
        print('categories',categories_list)
        return {"categories": categories_list}
    except Exception as e:
        print(f"Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.post('/productList')
async def productList(request: Request,x_api_key: str = Header(..., alias='X-API-KEY')):
    try:
        verify_api_key(x_api_key)
        json_request = await request.json()
        search_query = json_request.get("search_query", "")
        category_id = json_request.get("category_id")
        attributes = json_request.get("attributes", {})
        if search_query:
            search_query = search_query.strip()
            try:
                spell = SpellChecker()
                search_query = ' '.join(
                    [spell.correction(word) or word for word in search_query.split()])
            except Exception as e:
                print(f"Spell check error: {e}")
        match = {}
        if category_id:
            match["category_id"] = ObjectId(category_id)
        if attributes and isinstance(attributes, dict):
            for attribute_name, attribute_values in attributes.items():
                if attribute_values and isinstance(attribute_values, list):
                    match[f"attributes.{attribute_name}"] = {
                        "$in": attribute_values}
        pipeline = [{"$match": match}]
        pipeline.extend([
            {
                "$lookup": {
                    "from": "product_category",
                    "localField": "category_id",
                    "foreignField": "_id",
                    "as": "product_category_ins"
                }
            },
            {
                "$unwind": "$product_category_ins"
            },
            {
                "$match": {
                    "$or": [
                        {"brand_name": {"$regex": search_query, "$options": "i"}},
                        {"product_category_ins.name": {
                            "$regex": search_query, "$options": "i"}},
                        {"sku_number_product_code_item_number": {
                            "$regex": search_query, "$options": "i"}},
                        {"mpn": {"$regex": search_query, "$options": "i"}},
                        {"model": {"$regex": search_query, "$options": "i"}},
                        {"upc_ean": {"$regex": search_query, "$options": "i"}},
                        {"product_name": {"$regex": f'^{search_query}$', "$options": "i"}},
                        {
                            "$expr": {
                                "$gt": [
                                    {
                                        "$size": {
                                            "$filter": {
                                                "input": {"$objectToArray": "$attributes"},
                                                "cond": {
                                                    "$or": [
                                                        {
                                                            "$and": [
                                                                {"$eq": [
                                                                    {"$type": "$$this.k"}, "string"]},
                                                                {"$regexMatch": {
                                                                    "input": "$$this.k", "regex": search_query, "options": "i"}}
                                                            ]
                                                        },
                                                        {
                                                            "$and": [
                                                                {"$eq": [
                                                                    {"$type": "$$this.v"}, "string"]},
                                                                {"$regexMatch": {
                                                                    "input": "$$this.v", "regex": search_query, "options": "i"}}
                                                            ]
                                                        },
                                                        {
                                                            "$and": [
                                                                {"$in": [{"$type": "$$this.v"}, [
                                                                    "int", "long", "double", "decimal"]]},
                                                                {"$regexMatch": {
                                                                    "input": {"$toString": "$$this.v"}, "regex": search_query, "options": "i"}}
                                                            ]
                                                        }
                                                    ]
                                                }
                                            }
                                        }
                                    },
                                    0
                                ]
                            }
                        },
                        {"long_description": {"$regex": search_query, "$options": "i"}},
                        {"features": {"$regex": search_query, "$options": "i"}},
                    ]
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "id": {"$toString": "$_id"},
                    "image_url": {"$ifNull": [{"$first": "$images"}, "http://example.com/"]},
                    "sku": {"$ifNull": ["$sku_number_product_code_item_number", "N/A"]},
                    "name": {"$ifNull": ["$product_name", "N/A"]},
                    "category": "$product_category_ins.name",
                    "price": {"$ifNull": [{"$round": ["$list_price", 2]}, 0.0]},
                    "mpn": {"$ifNull": ["$mpn", "N/A"]},
                    "brand_name": {"$ifNull": ["$brand_name", "N/A"]},
                }
            },
        ])
        product_list = list(ShopifyProduct.objects.aggregate(*pipeline))
        return {"data": {"products": product_list}}
    except Exception as e:
        print(f"Error fetching products: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get('/category_filters')  
async def category_filters_view(category_id: str = Query(...),  x_api_key: str = Header(..., alias='X-API-KEY')):
    try:
        verify_api_key(x_api_key)
        print(f"Category ID: {category_id}")
        category_obj = product_category.objects.get(id=ObjectId(category_id))
        category_name = category_obj.name
        filters_cursor = filter.objects(category_id=ObjectId(category_id))
        filters_list = []
        for ins in filters_cursor:
            f = ins.to_mongo().to_dict()
            f.pop('_id', None)
            f.pop('category_id', None)
            if f.get('config', {}).get('options', []):
                for key, value in f.items():
                    if pd.isna(value) or value == float('nan'):
                        f[key] = None
                filters_list.append(f)
        filters_list = sorted(filters_list, key=lambda x: x.get('name', '').lower())
        return {
            "data": {
                "category_id": category_id,
                "category_name": category_name,
                "filters": filters_list
            }
        }
    except product_category.DoesNotExist:
        raise HTTPException(status_code=404, detail=f"Category {category_id} not found")
    except Exception as e:
        print(f"Error fetching filters: {e}")
        raise HTTPException(status_code=500, detail=str(e))