from fastapi import APIRouter, Header, HTTPException, Request,Query
from typing import List
from models.schemas import product_category, QuestionResponse, ShopifyProduct,filter
from services.auth import verify_api_key
from bson import ObjectId
import pandas as pd
from typing import Optional
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
        return {"data": {"categories": categories_list}}
    except Exception as e:
        print(f"Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get('/products')
async def get_products_filtered(
    request: Request,
    x_api_key: str = Header(..., alias='X-API-KEY'),
    category: Optional[str] = Query(None),
    search_query: Optional[str] = Query(None, alias='search'),
    brand: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
):
    """
    GET version of /productList for URL-based filtering
    """
    print("\n" + "="*60)
    print("🔍 GET /products REQUEST")
    print("="*60)
    print(f"📋 Category: {category}")
    print(f"📋 Brand: {brand}")
    print(f"📋 Color: {color}")
    print("="*60 + "\n")
    try:
        verify_api_key(x_api_key)
        match = {}
        if category:
            try:
                match["category_id"] = ObjectId(category)
            except Exception as e:
                print(f"Invalid category ID: {e}")
                return {"products": []}
        if brand:
            brand_list = [b.strip() for b in brand.split(',')]
            brand_regex = '|'.join(brand_list)  
            match["$or"] = [
                {"title": {"$regex": f"\\b({brand_regex})\\b", "$options": "i"}},
                {"tags": {"$in": [b.lower() for b in brand_list]}},
            ]
        attributes = {}
        if color:
            attributes['Color'] = color.split(',')
        if attributes:
            for attribute_name, attribute_values in attributes.items():
                if attribute_values:
                    match[f"attributes.{attribute_name}"] = {"$in": attribute_values}
        print(f"🔍 Match query: {match}")
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
            }
        ])
        if search_query and search_query.strip():
            search_query = search_query.strip()
            pipeline.append({
                "$match": {
                    "$or": [
                        {"brand_name": {"$regex": search_query, "$options": "i"}},
                        {"product_name": {"$regex": search_query, "$options": "i"}},
                        {"sku_number_product_code_item_number": {"$regex": search_query, "$options": "i"}},
                    ]
                }
            })
        pipeline.append({
    "$project": {
        "_id": 0,
        "id": {"$toString": "$_id"},
        "shopify_id": "$_id",
        "handle": {"$ifNull": ["$handle", ""]},  
        "variant_id": {"$ifNull": [{"$first": "$variants.id"}, None]},  
        "image": {"$ifNull": ["$image_url", "https://via.placeholder.com/300"]},
        "title": {"$ifNull": ["$title", "Untitled"]},
        "sku": {"$ifNull": [{"$first": "$variants.sku"}, "N/A"]},
        "category": {"$ifNull": ["$product_category_ins.name", "Uncategorized"]},
        "breadcrumb":{"$ifNull": ["$product_category_ins.breadcrumb", ""]},   
        "price": {"$ifNull": [{"$first": "$variants.price"}, 0]},
        "description": {"$ifNull": ["$body_html", ""]},
        "tags": {"$ifNull": ["$tags", []]},
        "vendor": {"$ifNull": ["$vendor", ""]},
    }
})
        print(f"🔍 Running aggregation pipeline...")
        product_list = list(ShopifyProduct.objects.aggregate(*pipeline))
        for product in product_list:
            product['price'] = f"${product.get('price', 0)} USD"
            if not product.get('image'):
                product['image'] = 'https://via.placeholder.com/300'
            if product.get('handle'):
                product['handle'] = product['handle'].lower().replace(' ', '-').replace('/', '-')
        print(f"✅ Found {len(product_list)} products")
        print(f"📦 Sample product: {product_list[0] if product_list else 'None'}")
        return {"products": product_list}
    except Exception as e:
        print(f"❌ Error in /products endpoint: {e}")
        import traceback
        traceback.print_exc()
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