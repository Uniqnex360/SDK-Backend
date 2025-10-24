from typing import Optional
from dateutil import parser
from datetime import datetime
from fastapi import APIRouter, Header, HTTPException
from models.schemas import ChatRequest, ChatResponse, ProductRequest, ShopifyProduct,product_category
from mongoengine import ReferenceField
from services.auth import verify_api_key, check_rate_limit
from typing import Dict, Any
import os
import asyncio
import httpx
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
SHOPIFY_STORE = os.getenv("SHOPIFY_STORE")
TOKEN = os.getenv("TOKEN")
router = APIRouter()


def parse_shopify_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    try:

        return parser.isoparse(date_str)
    except Exception as e:
        logger.warning(f"Failed to parse date {date_str}: {e}")
        return None


async def save_product_to_db(product_data: dict):
    product_type_name=product_data.get('product_data',"").strip()
    category_obj=None
    if product_type_name:
        category_obj=product_category.objects(name=product_type_name).first()
        if category_obj:
            logger.info(f"Found matching category: {category_obj.name} for product_type: {product_type_name}")
        else:
            logger.warning(f"No matching category found for product_type: {product_type_name}")

    product_doc = {
        "_id": product_data["id"],
        "title": product_data.get("title"),
        "vendor": product_data.get("vendor"),
        "product_type": product_data.get("product_type"),
        "handle": product_data.get("handle"),
        "tags": product_data.get("tags", "").split(",") if product_data.get("tags") else [],
        "status": product_data.get("status"),
        "body_html": product_data.get("body_html"),
        "image_url": product_data.get("image", {}).get("src"),
        "variants": [
            {
                "id": v.get("id"),
                "sku": v.get("sku"),
                "price": float(v.get("price", 0)),
                "inventory_quantity": v.get("inventory_quantity"),
                "barcode": v.get("barcode"),
                "weight": v.get("weight"),
                "weight_unit": v.get("weight_unit"),
            }
            for v in product_data.get("variants", [])
        ],
        "created_at": parse_shopify_date(product_data.get("created_at")),
        "updated_at": parse_shopify_date(product_data.get("updated_at")),
        "shopify_updated_at": parse_shopify_date(product_data.get("updated_at")),
        "category_id": category_obj
    }

    existing_product = ShopifyProduct.objects(_id=product_doc["_id"]).first()
    if existing_product:

        existing_product.update(**product_doc)
        saved_product = ShopifyProduct.objects(_id=product_doc["_id"]).first()
    else:

        saved_product = ShopifyProduct(**product_doc)
        saved_product.save()
    logger.info(f"Saved Shopify product ID: {saved_product._id}")
    print("Saved product with ID:", saved_product._id)
    return saved_product.to_dict()


@router.post('/product')
async def get_product_details(product_id: str, x_api_key: str) -> Dict[str, Any]:
    try:
        logger.info(f"Fetching Shopify product ID: {product_id}")
        config = verify_api_key(x_api_key)
        check_rate_limit(x_api_key, config['rate_limit'])
        url = f"https://{SHOPIFY_STORE}/admin/api/2025-01/products/{product_id}.json"
        headers = {
            "X-Shopify-Access-Token": TOKEN,
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
        product_data = response.json().get('product')
        if not product_data:
            raise HTTPException(status_code=404, detail="Product not found")
        logger.info(f"Fetched product: {product_data['title']}")

        variants = product_data.get('variants', [])
        first_variant = variants[0] if variants else {}

        product_context = {
            'productId': int(product_data.get('id')),
            'sku': first_variant.get('sku') or str(product_data.get('id')),
            'title': product_data.get('title'),
            'name': product_data.get('title'),
            'description': strip_html_tags(product_data.get('body_html', '')),
            'price': float(first_variant.get('price', 0)),
            'currency': 'USD',
            'brand': product_data.get('vendor', ''),
            'vendor': product_data.get('vendor', ''),
            'category': product_data.get('product_type', ''),
            'type': product_data.get('product_type', ''),
            'images': [img.get('src') for img in product_data.get('images', [])],
            'url': f"https://{SHOPIFY_STORE.replace('.myshopify.com', '')}/products/{product_data.get('handle')}",
            'handle': product_data.get('handle'),
            'inStock': first_variant.get('inventory_quantity', 0) > 0,
            'available': first_variant.get('inventory_quantity', 0) > 0,
            'variants': [
                {
                    'id': v.get('id'),
                    'title': v.get('title'),
                    'sku': v.get('sku', ''),
                    'price': float(v.get('price', 0)),
                    'available': v.get('inventory_quantity', 0) > 0,
                    'inventory_quantity': v.get('inventory_quantity', 0)
                }
                for v in variants[:10]
            ]
        }
        logger.info(f"Transformed product context:")
        logger.info(f"  - ID: {product_context['productId']}")
        logger.info(f"  - SKU: {product_context['sku']}")
        logger.info(f"  - Title: {product_context['title']}")
        logger.info(
            f"  - Description length: {len(product_context.get('description', ''))}")

        await save_product_to_db(product_data)
        logger.info(f"Saved Shopify product ID: {product_id}")

        return product_context
    except httpx.HTTPStatusError as e:
        logger.error(f"Shopify API error: {e}")
        raise HTTPException(status_code=e.response.status_code,
                            detail=f"Shopify API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}")


def strip_html_tags(html_text: str) -> str:
    import re
    if not html_text:
        return ""
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', html_text)

    text = ' '.join(text.split())
    return text.strip()
