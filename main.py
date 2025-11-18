import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr

from database import db

app = FastAPI(title="Restaurants Reservation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Helpers
# -----------------------------
from bson import ObjectId

def to_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id format")

def serialize(doc: dict) -> dict:
    if not doc:
        return doc
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d["_id"])
        del d["_id"]
    # Convert datetime fields to isoformat
    for key, val in list(d.items()):
        if isinstance(val, datetime):
            d[key] = val.isoformat()
    return d


# -----------------------------
# Schemas for requests
# -----------------------------
class RegisterPayload(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None

class LoginPayload(BaseModel):
    email: EmailStr

class ReservationPayload(BaseModel):
    customer_id: str
    restaurant_id: str
    reservation_time: str = Field(..., description="ISO datetime string")
    party_size: int = Field(..., ge=1, le=20)
    table_id: Optional[str] = None
    notes: Optional[str] = None


# -----------------------------
# Basic
# -----------------------------
@app.get("/")
def read_root():
    return {"message": "Restaurants Reservation API running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Connected & Working"
            response["connection_status"] = "Connected"
            response["collections"] = db.list_collection_names()[:10]
    except Exception as e:
        response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
    return response


# -----------------------------
# Seed demo data
# -----------------------------
@app.post("/api/seed")
def seed_demo():
    if db is None:
        raise HTTPException(500, "Database not configured")

    if db["restaurant"].count_documents({}) > 0:
        return {"message": "Already seeded"}

    demo = [
        {
            "name": "Blue Flame Bistro",
            "description": "Modern fusion cuisine with coastal vibes.",
            "thumbnail_url": "https://images.unsplash.com/photo-1559339352-11d035aa65de?q=80&w=1600&auto=format&fit=crop",
            "images": [
                "https://images.unsplash.com/photo-1528605248644-14dd04022da1?q=80&w=1600&auto=format&fit=crop",
                "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?q=80&w=1600&auto=format&fit=crop"
            ],
            "phone": "+1 202 555 0142",
            "email": "contact@blueflame.example",
            "address": "100 Ocean Ave, Bay City",
            "location_lat": 37.7749,
            "location_lng": -122.4194,
            "tables": [
                {"table_id": "T1", "size": 2},
                {"table_id": "T2", "size": 4},
                {"table_id": "T3", "size": 6}
            ],
            "menu": [
                {"name": "Seared Tuna", "description": "With sesame crust", "price": 22.5, "category": "Mains"},
                {"name": "Citrus Salad", "description": "Grapefruit & fennel", "price": 12.0, "category": "Starters"}
            ]
        },
        {
            "name": "Garden Table",
            "description": "Farm-to-table seasonal dishes.",
            "thumbnail_url": "https://images.unsplash.com/photo-1541542684-4a3a0c238f8b?q=80&w=1600&auto=format&fit=crop",
            "images": [
                "https://images.unsplash.com/photo-1559339352-11d035aa65de?q=80&w=1600&auto=format&fit=crop"
            ],
            "phone": "+1 202 555 0198",
            "email": "hello@gardentable.example",
            "address": "50 Green St, Meadow Town",
            "location_lat": 34.0522,
            "location_lng": -118.2437,
            "tables": [
                {"table_id": "A1", "size": 2},
                {"table_id": "A2", "size": 4}
            ],
            "menu": [
                {"name": "Roast Chicken", "description": "With herbs", "price": 18.0, "category": "Mains"},
                {"name": "Heirloom Tomato", "description": "Burrata & basil", "price": 10.0, "category": "Starters"}
            ]
        }
    ]
    db["restaurant"].insert_many(demo)
    return {"message": "Seeded demo restaurants", "count": len(demo)}


# -----------------------------
# Auth (simple demo)
# -----------------------------
@app.post("/api/customers/register")
def register(payload: RegisterPayload):
    existing = db["customer"].find_one({"email": payload.email})
    if existing:
        raise HTTPException(409, "Email already registered")
    doc = {
        "name": payload.name,
        "email": payload.email,
        "phone": payload.phone,
        "loyalty_points": 0,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    res = db["customer"].insert_one(doc)
    doc["id"] = str(res.inserted_id)
    return doc

@app.post("/api/customers/login")
def login(payload: LoginPayload):
    user = db["customer"].find_one({"email": payload.email})
    if not user:
        raise HTTPException(404, "Account not found. Please register.")
    return serialize(user)


# -----------------------------
# Customer profile, activities, loyalty
# -----------------------------
@app.get("/api/customers/{customer_id}")
def get_profile(customer_id: str):
    doc = db["customer"].find_one({"_id": to_object_id(customer_id)})
    if not doc:
        raise HTTPException(404, "Customer not found")
    return serialize(doc)

class UpdateProfilePayload(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None

@app.put("/api/customers/{customer_id}")
def update_profile(customer_id: str, payload: UpdateProfilePayload):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.utcnow()
    res = db["customer"].find_one_and_update(
        {"_id": to_object_id(customer_id)}, {"$set": updates}, return_document=True
    )
    if not res:
        raise HTTPException(404, "Customer not found")
    return serialize(res)

@app.get("/api/customers/{customer_id}/activities")
def activities(customer_id: str, limit: int = Query(10, ge=1, le=50)):
    items = list(
        db["activity"].find({"customer_id": customer_id}).sort("_id", -1).limit(limit)
    )
    return [serialize(i) for i in items]

@app.get("/api/customers/{customer_id}/loyalty")
def loyalty(customer_id: str):
    user = db["customer"].find_one({"_id": to_object_id(customer_id)})
    if not user:
        raise HTTPException(404, "Customer not found")
    return {"loyalty_points": int(user.get("loyalty_points", 0))}


# -----------------------------
# Restaurants
# -----------------------------
@app.get("/api/restaurants")
def list_restaurants():
    items = list(db["restaurant"].find({}))
    return [serialize(i) for i in items]

@app.get("/api/restaurants/{restaurant_id}")
def restaurant_detail(restaurant_id: str):
    doc = db["restaurant"].find_one({"_id": to_object_id(restaurant_id)})
    if not doc:
        raise HTTPException(404, "Restaurant not found")
    return serialize(doc)


# -----------------------------
# Reservations & Waitlist
# -----------------------------
@app.get("/api/customers/{customer_id}/reservations")
def customer_reservations(customer_id: str, status: Optional[str] = None):
    q = {"customer_id": customer_id}
    if status == "upcoming":
        q["status"] = {"$in": ["confirmed", "waitlisted"]}
    elif status == "past":
        q["status"] = "completed"
    items = list(db["reservation"].find(q).sort("reservation_time", 1))
    return [serialize(i) for i in items]

@app.get("/api/customers/{customer_id}/waitlist")
def customer_waitlist(customer_id: str):
    items = list(db["waitlist"].find({"customer_id": customer_id}).sort("_id", 1))
    return [serialize(i) for i in items]


def _find_available_table(restaurant: dict, reservation_time: str, party_size: int) -> Optional[str]:
    tables = restaurant.get("tables", [])
    suitable = [t for t in tables if int(t.get("size", 0)) >= party_size]
    # find reservations at same time
    existing = list(db["reservation"].find({
        "restaurant_id": str(restaurant["_id"]),
        "reservation_time": reservation_time,
        "status": {"$in": ["confirmed"]}
    }))
    unavailable_ids = {r.get("table_id") for r in existing if r.get("table_id")}
    for t in suitable:
        if t["table_id"] not in unavailable_ids:
            return t["table_id"]
    return None

@app.post("/api/reservations")
def create_reservation(payload: ReservationPayload):
    # Validate customer and restaurant
    customer = db["customer"].find_one({"_id": to_object_id(payload.customer_id)})
    if not customer:
        raise HTTPException(404, "Customer not found")
    restaurant = db["restaurant"].find_one({"_id": to_object_id(payload.restaurant_id)})
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")

    # Assign table if not provided
    table_id = payload.table_id
    if not table_id:
        table_id = _find_available_table(restaurant, payload.reservation_time, payload.party_size)

    if not table_id:
        # No table available -> add to waitlist
        wait_doc = {
            "customer_id": payload.customer_id,
            "restaurant_id": payload.restaurant_id,
            "desired_time": payload.reservation_time,
            "party_size": payload.party_size,
            "status": "waiting",
            "created_at": datetime.utcnow(),
        }
        db["waitlist"].insert_one(wait_doc)
        db["activity"].insert_one({
            "customer_id": payload.customer_id,
            "type": "waitlist",
            "message": f"Added to waitlist for {restaurant['name']} on {payload.reservation_time}",
            "created_at": datetime.utcnow(),
        })
        return {"status": "waitlisted", "message": "No tables available. You are added to the waitlist."}

    # Create reservation
    res_doc = {
        "customer_id": payload.customer_id,
        "restaurant_id": payload.restaurant_id,
        "reservation_time": payload.reservation_time,
        "party_size": payload.party_size,
        "table_id": table_id,
        "status": "confirmed",
        "notes": payload.notes,
        "created_at": datetime.utcnow(),
    }
    db["reservation"].insert_one(res_doc)

    # Increment loyalty points (simple rule)
    db["customer"].update_one({"_id": to_object_id(payload.customer_id)}, {"$inc": {"loyalty_points": 10}})

    db["activity"].insert_one({
        "customer_id": payload.customer_id,
        "type": "reservation",
        "message": f"Reservation confirmed at {restaurant['name']} (table {table_id})",
        "created_at": datetime.utcnow(),
    })

    return {"status": "confirmed", "reservation": res_doc}

