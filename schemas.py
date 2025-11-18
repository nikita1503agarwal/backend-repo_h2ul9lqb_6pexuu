"""
Database Schemas for the Restaurants Reservation System

Each Pydantic model below represents a MongoDB collection. The collection
name is the lowercase of the class name. Example: class Customer -> "customer".

These schemas are used for validation when creating/editing documents and also
serve as living documentation for the data model.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr


class Customer(BaseModel):
    """Customers who use the platform"""
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Unique email address")
    phone: Optional[str] = Field(None, description="Phone number")
    avatar_url: Optional[str] = Field(None, description="Profile photo URL")
    loyalty_points: int = Field(0, ge=0, description="Accumulated loyalty points")
    preferences: Optional[List[str]] = Field(default_factory=list, description="Cuisine or seating preferences")
    is_active: bool = Field(True, description="Whether the account is active")


class Table(BaseModel):
    """Embedded structure used inside Restaurant"""
    table_id: str = Field(..., description="Unique table identifier within the restaurant")
    size: int = Field(..., ge=1, le=20, description="Max number of guests for the table")


class MenuItem(BaseModel):
    name: str = Field(...)
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    category: Optional[str] = None
    image_url: Optional[str] = None


class Restaurant(BaseModel):
    name: str = Field(...)
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    images: Optional[List[str]] = Field(default_factory=list)
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    location_lat: Optional[float] = Field(None, description="Latitude")
    location_lng: Optional[float] = Field(None, description="Longitude")
    tables: List[Table] = Field(default_factory=list)
    menu: List[MenuItem] = Field(default_factory=list)


class Reservation(BaseModel):
    customer_id: str = Field(..., description="ObjectId of the customer as string")
    restaurant_id: str = Field(..., description="ObjectId of the restaurant as string")
    reservation_time: str = Field(..., description="ISO datetime string")
    party_size: int = Field(..., ge=1, le=20)
    table_id: Optional[str] = Field(None, description="Chosen/assigned table id")
    status: str = Field("confirmed", description="confirmed | waitlisted | cancelled")
    notes: Optional[str] = None


class Activity(BaseModel):
    customer_id: str
    type: str = Field(..., description="reservation|waitlist|profile|loyalty|other")
    message: str


class Waitlist(BaseModel):
    customer_id: str
    restaurant_id: str
    desired_time: str = Field(..., description="ISO datetime string")
    party_size: int = Field(..., ge=1, le=20)
    status: str = Field("waiting", description="waiting | notified | expired")
    position: Optional[int] = None
