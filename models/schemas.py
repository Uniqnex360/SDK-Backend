from pydantic import BaseModel 
from mongoengine import fields, Document
from datetime import datetime
from typing import Optional, List
from mongoengine import connect
from typing import Dict, Any, Optional  
from mongoengine import ReferenceField
import os
import asyncio
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
MONGODB_HOST = os.getenv("MONGODB_HOST")
MONGODB_NAME = os.getenv("MONGODB_NAME")
print(MONGODB_HOST)
print(MONGODB_NAME)

try:
    connect(
        db=MONGODB_NAME,
        host=MONGODB_HOST,
        alias="default"
    )
    print("✅ MongoDB connected!")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    raise
class ProductRequest(BaseModel):
    product_id:int
class ProductResponse(BaseModel):
    id:int
    title:int
    body_html:str
class ChatRequest(BaseModel):
    message: str
    product_context: Dict[str, Any]  
    session_id: Optional[str] = None
class ChatResponse(BaseModel):
    response: str
    session_id: str
    product_id: Optional[str] = None  
class QuestionResponse(BaseModel):
    id:str
    question:str
class product_category(Document):
    name = fields.StringField(required=True)
    level = fields.IntField(default=0)
    parent_category_id = fields.ReferenceField('self', null=True)
    child_categories = fields.ListField(fields.ReferenceField('self'))
    breadcrumb = fields.StringField()
    manufacture_unit_id_str = fields.StringField()
    creation_date = fields.DateTimeField(default=datetime.now())
    description = fields.StringField()
    code = fields.StringField()
    end_level = fields.BooleanField(default=False)
    industry_id_str = fields.StringField()
class ConfigResponse(BaseModel):
    theme:dict
    position:str
    greeting_message:str
    placeholder:str
class brand(Document):
    name = fields.StringField(required=True)
    code = fields.StringField()
    product_sub_category_id_str = fields.StringField()
    logo = fields.StringField()
    manufacture_unit_id_str = fields.StringField()
    industry_id_str = fields.StringField()
class vendor(Document):
    name = fields.StringField(required=True)
    manufacture_unit_id_str = fields.StringField()
class manufacture_unit(Document):
    name = fields.StringField()
    description = fields.StringField()
    location = fields.StringField()
    logo = fields.StringField()
    industry = fields.StringField()
    is_active = fields.BooleanField(default=True)
class product(Document):
    sku_number_product_code_item_number = fields.StringField(default="")
    model = fields.StringField()
    mpn = fields.StringField(default="")
    upc_ean = fields.StringField()
    breadcrumb = fields.StringField()
    brand_name = fields.StringField(default="")
    product_name = fields.StringField(default="")
    long_description = fields.StringField(default="")
    short_description = fields.StringField()
    features = fields.ListField(fields.StringField())
    images = fields.ListField(fields.StringField())
    attributes = fields.DictField(default={})
    tags = fields.ListField(fields.StringField())
    msrp = fields.FloatField(default=0.0)
    currency = fields.StringField(default="")
    was_price = fields.FloatField(default=0.0)
    list_price = fields.FloatField(default=0.0)
    discount = fields.FloatField(default=0.0)
    quantity_prices = fields.FloatField(default=0.0)
    quantity = fields.FloatField()
    availability = fields.BooleanField(default=True)
    return_applicable = fields.BooleanField(default=False)
    return_in_days = fields.StringField()
    visible = fields.BooleanField(default=True)
    brand_id = fields.ReferenceField(brand)
    vendor_id = fields.ReferenceField(vendor)
    category_id = fields.ReferenceField(product_category)
    quantity_price = fields.DictField(
        default={"1-100": 1, "100-1000": 2, "1000-10000": 3})
    rating_count = fields.IntField(default=0)
    rating_average = fields.FloatField(default=0.0)
    from_the_manufacture = fields.StringField()
    industry_id_str = fields.StringField()
    tax = fields.FloatField(default=0.0)
    manufacture_unit_id = fields.ReferenceField(manufacture_unit)
    old_names = fields.ListField(fields.StringField())
    old_description = fields.ListField(fields.StringField())
    old_features = fields.ListField(fields.ListField(fields.StringField()))
    ai_generated_title = fields.ListField(fields.DictField())
    ai_generated_description = fields.ListField(fields.DictField())
    ai_generated_features = fields.ListField(fields.DictField())
from mongoengine import Document, IntField, StringField, ListField, DictField, DateTimeField, FloatField
class ShopifyProduct(Document):
    _id = IntField(primary_key=True)  
    title = StringField(required=True)
    vendor = StringField()
    product_type = StringField()
    handle = StringField()
    tags = ListField(StringField())
    status = StringField()
    body_html = StringField()
    image_url = StringField()
    variants = ListField(DictField())  
    created_at = DateTimeField()
    updated_at = DateTimeField()
    shopify_updated_at = DateTimeField()  
    last_synced = DateTimeField(default=datetime.now)
    category_id=ReferenceField(product_category,null=True)
    meta = {"collection": "shopify_products"} 
    def to_dict(self):
        return {
            "_id": self._id,
            "title": self.title,
            "vendor": self.vendor,
            "product_type": self.product_type,
            "handle": self.handle,
            "tags": self.tags,
            "status": self.status,
            "body_html": self.body_html,
            "image_url": self.image_url,
            "variants": self.variants,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "shopify_updated_at": self.shopify_updated_at,
            "last_synced": self.last_synced,
            "category_id": str(self.category_id.id) if self.category_id else None
        }
class product_questions(Document):
    question = fields.StringField()
    answer = fields.StringField()
    question_type = fields.StringField()
    product_id = fields.ReferenceField(product)
    category_id = fields.ReferenceField(product_category)
    
def save_questions_from_excel(file_path):
    df=pd.read_excel(file_path)
    for _,row in df.iterrows():
        category_names=[
            str(row.get(f"C-{i}", "")).strip()
            for i in range(1,6)
            if pd.notna(row.get(f"C-{i}", "")) and str(row.get(f"C-{i}", "")).strip()
            
        ]
        category_name=str(row.get('Product Type',"")).strip()
        if not category_name:
            category_name='Unauthorized'
        category_obj=product_category.objects(name=category_name).first()
        if not category_obj:
            category_obj=product_category(
                name=category_name,
                breadcrumb=" -> ".join(category_names),
                end_level=True
            ).save()
        question_txt=str(row.get("Questions","")).strip()
        answer_txt=str(row.get("Answer","")).strip()
        question_type=str(row.get('Question Type',"")).strip()
        if not question_txt or not answer_txt:
            continue
        exisiting=product_questions.objects(
            question=question_txt,
            category_id=category_obj
        ).first()
        if exisiting:
            print(f"Skipping duplicate questions:{question_txt}")
            continue
        product_questions(
            question=question_txt,
            answer=answer_txt,
            question_type=question_type,
            category_id=category_obj
        ).save()
        print(f"Saved question :{question_txt}")
# save_questions_from_excel("/home/lexicon/Downloads/Shopify - 27 Category - FAQ's - updated-1.xlsx")