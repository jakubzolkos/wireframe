from dataclasses import dataclass
import re
import sys
import json
from typing import Literal, Optional
from urllib.parse import unquote

from pydantic import BaseModel

from app.core.clients import get_ultralibrarian_client, get_digikey_client

from autopcb.datatypes.schematics import LibSymbol
from autopcb.datatypes.pcb import Footprint
from fastapi import APIRouter, HTTPException

from autopcb.datatypes.templates import GNDSymbol, NetLabelSymbol, NoConnectSymbol, PowerSymbol
from autopcb.datatypes.mixins import DataclassSerializerMixin

@dataclass
class ParsedChip(DataclassSerializerMixin):
    symbol: LibSymbol
    # Optional for symbols like GND which don't have a footprint
    footprint: Footprint | None = None

router = APIRouter()


class ChipSearchItem(BaseModel):
    uid: str
    mpn: str
    manufacturer: str
    symbol: LibSymbol
    footprint: Footprint | None = None
    datasheet: str | None = None
    description: str | None = None
    package: str | None = None
    source: Literal["ultralibrarian", "jlc", "digikey"]


@router.get("/")
async def get_chip(chip_id: str) -> ParsedChip:
    """
    Get chip data from the database that matches specific chip_id (could be MPN, JLC ID, or a template symbol)
    """
    chip_id = unquote(chip_id)

    try:
        if chip_id == 'GND':
            return ParsedChip(symbol=GNDSymbol('GND'))
        elif chip_id == 'VCC':
            return ParsedChip(symbol=PowerSymbol('VCC'))
        elif chip_id == 'NoConnect':
            return ParsedChip(symbol=NoConnectSymbol('NoConnect'))
        elif chip_id.startswith('NetLabel'):
            return ParsedChip(symbol=NetLabelSymbol(chip_id.split('-')[1]))

        ul_client = get_ultralibrarian_client()
        mfr, mpn = chip_id.rsplit('/', 1)
        valid_parts = ul_client.search_chips_by_manufacturer_info([{"mpn": mpn, "mfr": mfr}])
        uid = valid_parts.get(mpn, {}).get('part_response', {}).get('part_data', {}).get('uid')
        if not uid:
            raise HTTPException(status_code=404, detail="No part found with the given MPN and manufacturer")

        return ul_client.get_chip(uid)
            
    except Exception as e:
        print(f"Failed to fetch chip {chip_id}: {e}", file=sys.stderr)
        raise HTTPException(status_code=400, detail=f"Failed to fetch chip: {str(e)}")


@router.get("/search")
async def search_chips(
    keywords: Optional[str] = None,
    category_id: Optional[str] = None,
    filters: str = "{}",
    search_limit: int = 10,
    result_limit: int = 1,
    supplier: Literal["jlc", "digikey"] = "digikey"
) -> list[ChipSearchItem]:
    """
    Search using keywords (MPN search) and/or parametric filters from either JLC or Digikey.

    Supports two modes:
    1. Keyword search: Search by manufacturer part number (MPN)
       - Used in SubcircuitToolbar for quick part lookup
    2. Parametric search: Filter by component parameters (resistance, capacitance, etc.)
       - Used in Part declarations for finding components by specs

    Args:
        keywords: Search keywords (e.g., manufacturer part number)
        category_id: Category ID (required for parametric search)
        filters: JSON string of filter key-value pairs (for parametric search)
        search_limit: Maximum number of results to fetch from supplier (default: 10)
        result_limit: Maximum number of results with symbols to return (default: 1)
        supplier: Supplier to use - either 'jlc' or 'digikey' (default: 'digikey')

    Returns:
        List of ChipSearchItem with symbols and footprints from UltraLibrarian

    Examples:
        # Keyword search for MPN
        GET /search?keywords=STM32F407VGT6&limit=5

        # Parametric search for 10kΩ resistors from Digikey
        GET /search?category_id=52&filters={"resistance":"10~10 kΩ","tolerance":["±1%"]}&limit=20

        # Parametric search from JLC
        GET /search?supplier=jlc&category_id=Capacitors&filters={"capacitance":"10~100 uF"}&limit=20
    """
    ul_client = get_ultralibrarian_client()

    try:
        filter_dict = json.loads(filters) if filters != "{}" else {}

        digikey_client = get_digikey_client()

        # Parse and convert filters for parametric search
        digikey_filters = []
        if category_id and filter_dict:
            digikey_filters = digikey_client.convert_to_digikey_filters(filter_dict, category_id)

        # Perform search (keyword, parametric, or combined)
        search_response = digikey_client.search_chips(
            keywords=keywords or "",
            category_id=category_id,
            parametric_filters=digikey_filters if digikey_filters else None,
            search_options=["InStock"],
            limit=search_limit
        )

        products = search_response.get("Products", [])
        if not products:
            raise HTTPException(
                status_code=404,
                detail="No components found matching the specified filters"
            )

        # Build batch request for UltraLibrarian
        parts_to_search = []
        for product in products:
            mpn = product.get("ManufacturerProductNumber", "")
            manufacturer_data = product.get("Manufacturer", {})
            manufacturer = manufacturer_data.get("Name", "") if isinstance(manufacturer_data, dict) else ""

            if mpn and manufacturer:
                parts_to_search.append({
                    "mpn": mpn,
                    "mfr": manufacturer
                })

        # Batch search in UltraLibrarian
        ul_results = ul_client.search_chips_by_manufacturer_info(parts_to_search)

        # Match Digikey results with UltraLibrarian results and fetch symbols/footprints
        chip_items = []
        for product in products:
            mpn = product.get("ManufacturerProductNumber", "")
            manufacturer_data = product.get("Manufacturer", {})
            manufacturer = manufacturer_data.get("Name", "") if isinstance(manufacturer_data, dict) else ""

            # Check if UltraLibrarian has this part with symbol and footprint
            ul_part = ul_results.get(mpn)
            if ul_part:
                uid = ul_part.get("part_response").get("part_data").get("uid")
                if uid:
                    # Fetch symbol and footprint using cached method
                    parsed_chip = ul_client.get_chip(uid)

                    chip_items.append(ChipSearchItem(
                        uid=mpn,
                        mpn=mpn,
                        manufacturer=manufacturer,
                        description=product.get("Description", {}).get("DetailedDescription", None),
                        datasheet=product.get("DatasheetUrl", None),
                        symbol=parsed_chip.symbol,
                        footprint=parsed_chip.footprint,
                        source="digikey"
                    ))

                    # Return once we have the requested number of results
                    if len(chip_items) >= result_limit:
                        break

        if not chip_items:
            raise HTTPException(
                status_code=404,
                detail="No components found with available symbols/footprints"
            )

        return chip_items

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in filters parameter")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Parametric search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: see backend logs for details")
