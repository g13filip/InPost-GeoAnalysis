from paczkomatoza.config import API_BASE, DATA_ROOT, PER_PAGE
import os
from pathlib import Path
import pandas as pd
from datetime import datetime, timezone
import asyncio
import json
import httpx
import unicodedata

from paczkomatoza.ingest.models import InPostPoint
from paczkomatoza.ingest.inpost_client import points_to_dataframe, fetch_page

def _slugify(text: str) -> str:
    text = text.replace("ł", "l").replace("Ł", "L")
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_str.lower().strip().replace(" ", "_").replace("-", "_")

def is_cached(city: str) -> bool:
    """Sprawdza, czy dla danego miasta istnieje już snapshot .parquet."""

    target_dir = DATA_ROOT / "raw" / "inpost"
    city_slug = _slugify(city)

    if not DATA_ROOT.exists():
        return False
    if not target_dir.exists():
        return False

    if any(target_dir.glob(f"{city_slug}_*.parquet")):
        return True

    return False

async def _check(city: str) -> bool:
    async with httpx.AsyncClient(timeout=10.0) as client:
        page = await fetch_page(client, city, page=1, per_page=1)
        return page.count > 0

def does_city_exist_in_api(city: str) -> bool:
    """Sprawdza, czy API InPost zwraca dane dla danego miasta — prosta weryfikacja przed uruchomieniem pipeline."""
    return asyncio.run(_check(city))



def save_city_data_parquet(city: str, 
                           points: list[InPostPoint],) -> None:

    city_slug = _slugify(city)
    target_dir = DATA_ROOT / "raw" / "inpost"
    target_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    df = points_to_dataframe(points)

    parquet_path = target_dir / f"{city_slug}_{today}.parquet"
    meta_path = target_dir / f"{city_slug}_{today}.meta.json"


    df.to_parquet(parquet_path, index=False)

    meta = {
        "city_slug": city_slug,
        "snapshot_date_utc": today,
        "snapshot_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": API_BASE,
        "per_page": PER_PAGE,
        "n_records": len(df),
        "n_unique_names": int(df["name"].nunique()) if "name" in df.columns else 0,
        "columns": list(df.columns),
        "file_size_bytes": parquet_path.stat().st_size,
    }

    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))

