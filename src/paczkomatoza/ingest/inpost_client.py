"""Klient API InPost z paginacją i retry."""

from __future__ import annotations

import pandas as pd
import httpx
import asyncio
from typing import Optional

from paczkomatoza.config import API_BASE, MAX_RETRIES, PER_PAGE
from paczkomatoza.ingest.models import InPostPage, InPostPoint

async def fetch_page(client: httpx.AsyncClient,
                     city: str,
                     page: int,
                     per_page: int) -> InPostPage:
    """Pobiera pojedynczą stronę wyników z API InPost."""

    params = {
        "city": city,
        "page": page,
        "per_page": per_page}
    
    last_exception: Optional[Exception] = None


    for attempt in range(MAX_RETRIES):
        try:
            response = await client.get(API_BASE, params=params)

            if response.status_code == 429 or response.status_code >= 500:
                response.raise_for_status()  # rzuci HTTPStatusError, który zostanie złapany i obsłużony retryem

            payload = response.json()
            return InPostPage.model_validate(payload)
        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.NetworkError) as e:
            last_exception = e
            response_code = e.response.status_code if isinstance(e, httpx.HTTPStatusError) else "N/A"

            if response_code != "N/A" and 400 <= response_code < 500 and response_code != 429:
                print(f"Nie retry'ujemy błędu {response_code} dla strony {page} (attemp {attempt + 1}/{MAX_RETRIES})")
                raise e
            
            if attempt < MAX_RETRIES - 1:
                backoff_time = 2 ** attempt
                print(f"Błąd {e} dla strony {page} (attemp {attempt + 1}/{MAX_RETRIES}). Retrying in {backoff_time} seconds...")
                await asyncio.sleep(backoff_time)
            else:
                print(f"Max retries reached for page {page}. Last error: {last_exception}")
                raise last_exception

    raise last_exception 



async def fetch_all_pages_for_city(city: str,
                                   per_page: int = PER_PAGE,
                                   ) -> list[InPostPoint]:
    """Pobiera wszystkie strony wyników dla danego miasta."""

    all_points: list[InPostPoint] = []

    async with httpx.AsyncClient(timeout = 30.0) as client:

        first_page = await fetch_page(client, city, page=1, per_page=per_page)
        all_points.extend(first_page.items)
        total_pages = first_page.total_pages

        if total_pages <= 1:
            return all_points
        
        for page in range(2, total_pages + 1):
            
            page_data = await fetch_page(client, city, page=page, per_page=per_page)
            all_points.extend(page_data.items)
            
    return all_points


def points_to_dataframe(points: list[InPostPoint]) -> pd.DataFrame:
    """Spłaszcza zagnieżdżony JSON (location.*, address_details.*) do DataFrame."""

    rows = []
    for p in points:
        d = p.model_dump()
        addr = d.pop("address_details", None) or {}
        loc = d.pop("location", None) or {}
        rows.append({
            **d,
            "latitude": loc.get("latitude"),
            "longitude": loc.get("longitude"),
            "city": addr.get("city"),
            "province": addr.get("province"),
            "post_code": addr.get("post_code"),
            "street": addr.get("street"),
            "building_number": addr.get("building_number"),
            "flat_number": addr.get("flat_number"),
        })
    return pd.DataFrame(rows)