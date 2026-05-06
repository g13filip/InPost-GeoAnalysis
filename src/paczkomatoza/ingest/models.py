"""Modele Pydantic dla odpowiedzi API InPost.

TODO: Zaimplementuj w oparciu o notebook 02_fetch_city_data.
Kluczowe struktury: InPostLocation, InPostAddressDetails,
InPostPoint (z walidacją statusu, typów funkcji), InPostPage.
"""
from __future__ import annotations
from pydantic import BaseModel, Field, ValidationError
from typing import Optional

class Location(BaseModel):
    """Współrzędne geograficzne punktu."""
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

class AddressDetails(BaseModel):
    """Adres jako rozbity na pola."""
    city: Optional[str] = None
    province: Optional[str] = None
    post_code: Optional[str] = None
    street: Optional[str] = None
    building_number: Optional[str] = None
    flat_number: Optional[str] = None


class InPostPoint(BaseModel):
    """Pojedynczy punkt odbioru z API InPost.
    
    Walidujemy tylko najważniejsze pola. Reszta jest akceptowana dzięki
    konfiguracji 'extra=\"allow\"' i będzie zachowana przy model_dump().
    """
    name: str  
    type: list[str]  
    status: Optional[str] = None  
    location: Location
    location_type: Optional[str] = None  
    address_details: Optional[AddressDetails] = None
    opening_hours: Optional[str] = None
    functions: Optional[list[str]] = None

    model_config = {"extra": "allow"}

class InPostPage(BaseModel):
    """Pojedyncza strona odpowiedzi z paginacją."""
    count: int
    page: int
    per_page: int
    total_pages: int
    items: list[InPostPoint]


