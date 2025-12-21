import re
import sys
import time
import json
from pathlib import Path
from typing import Any

import httpx
import structlog
from app.core.config import settings
from app.core.models import ChipCategory, ChipFilterMultichoice, ChipFilterMultichoiceValue, ChipFilterPhysicalUnitRange, ChipSubcategoryInfo

log = structlog.get_logger()

SI_prefixes = {
    'ppm': 1e-6,
    'ppb': 1e-9,
    'f': 1e-15,
    'p': 1e-12,
    'n': 1e-9,
    'μ': 1e-6,
    'µ': 1e-6,  # be careful, this is a different character than the line above
    'u': 1e-6,
    'm': 1e-3,
    'c': 1e-2,
    'd': 1e-1,
    'h': 100,
    'k': 1000,
    'K': 1000,  #  jlc_library/Embedded Processors and Controllers/Microcontroller Units (MCUs or MPUs or SOCs).json has KB and MB
    'M': 1e6,
    'G': 1e9,
    'T': 1e12,
}

def parse_physical_value(s: str) -> tuple[float, str]:
    """
    Parses a string representing a physical quantity and returns a tuple:
      (numeric_value_in_base_units, base_unit_string)

    Examples:
      "6kΩ"   -> (6000.0, "Ω")
      "6000Ω" -> (6000.0, "Ω")
      "mF"    -> (0.001, "F")
      "2A"    -> (2.0, "A")
      "3%"    -> (3.0, "%")
      ".25H   -> (0.25, "H")
      "200ppm/℃" -> (200.0, "ppm/℃")
    """
    # Clean up input - remove ± and extra spaces around + or -
    s = s.strip().replace("±", "").replace("+ ", "+").replace("- ", "-")

    number_regex = re.compile(r'^([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(.*)$')
    match = number_regex.match(s)
    if match:
        num_str = match.group(1)
        rest = match.group(2).strip()
        value = float(num_str)
    else:
        # If no numeric part is found, assume 1.
        value = 1.0
        rest = s

    if not rest:
        raise ValueError(f"No unit specified in {s!r}")

    # Special units that should not have prefix parsing (they contain letters that look like prefixes)
    special_units = ['ppm', 'ppb', 'ppt']  # parts per million/billion/trillion

    # Check if the unit starts with a special unit
    for special_unit in special_units:
        if rest.lower().startswith(special_unit):
            # Don't parse prefix for these units
            return value, rest

    # If the rest begins with a known metric prefix, separate it.
    if len(rest) > 1 and rest[0] in SI_prefixes:
        prefix = rest[0]
        unit = rest[1:]
        multiplier = SI_prefixes[prefix]
    else:
        multiplier = 1
        unit = rest

    return value * multiplier, unit


def parse_user_range_filter(filter_str: str) -> tuple[float | None, float | None, str]:
    """
    Parses user filter string in format: "", ">=X unit", "<=X unit", or "X~Y unit"
    Returns (min_value, max_value, unit) where values are in base units.

    Examples:
      ""                  -> (None, None, "")
      ">=4 kohm"          -> (4000.0, None, "ohm")
      "<=10 kohm"         -> (None, 10000.0, "ohm")
      "4~10 kohm"         -> (4000.0, 10000.0, "ohm")
      "1.5~3.3 V"         -> (1.5, 3.3, "V")
    """
    if not filter_str or filter_str.strip() == '':
        return (None, None, "")

    filter_str = filter_str.strip()

    # Match ">=X unit"
    ge_match = re.match(r'^>=\s*(.+)$', filter_str)
    if ge_match:
        min_val, unit = parse_physical_value(ge_match.group(1))
        return (min_val, None, unit)

    # Match "<=X unit"
    le_match = re.match(r'^<=\s*(.+)$', filter_str)
    if le_match:
        max_val, unit = parse_physical_value(le_match.group(1))
        return (None, max_val, unit)

    # Match "X~Y unit"
    range_match = re.match(r'^([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*~\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*(.+)$', filter_str)
    if range_match:
        min_str = range_match.group(1)
        max_str = range_match.group(2)
        unit_str = range_match.group(3).strip()

        min_val, unit = parse_physical_value(min_str + unit_str)
        max_val, _ = parse_physical_value(max_str + unit_str)
        return (min_val, max_val, unit)

    raise ValueError(f"Invalid range filter format: {filter_str}")


def generate_python_alias(param_name: str) -> str:
    """
    Generate a Python-friendly alias from a parameter name.
    Converts spaces and special characters to underscores, and makes it lowercase.
    """
    alias = param_name.lower().strip()
    alias = re.sub(r'[^a-z0-9_]+', '_', alias)
    alias = re.sub(r'_+', '_', alias)
    alias = alias.strip('_')
    if not alias or alias[0].isdigit():
        alias = 'param_' + alias
    return alias


class DigiKeyClient:
    """Async Client for interacting with DigiKey API"""

    def __init__(self):
        self.client_id = settings.DIGIKEY_CLIENT_ID
        self.client_secret = settings.DIGIKEY_CLIENT_SECRET
        self.token_url = "https://api.digikey.com/v1/oauth2/token"
        self.base_url = "https://api.digikey.com"
        self._access_token: str | None = None
        self._token_expiry: float | None = None
        self._token_issued_at: float | None = None
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self._client.aclose()

    def _clear_token_cache(self):
        """Clear the cached token to force a refresh"""
        self._access_token = None
        self._token_expiry = None
        self._token_issued_at = None

    def _is_token_valid(self) -> bool:
        """Check if the current token is still valid"""
        if not self._access_token or not self._token_expiry:
            return False

        now = time.time()
        # Consider token valid if it expires in more than 30 seconds
        return self._token_expiry > now + 30

    async def _get_access_token(self) -> str:
        """
        Get OAuth2 access token using client credentials flow.
        """
        # Use cached token if valid
        if self._is_token_valid():
            return self._access_token

        if not self.client_id or not self.client_secret:
            raise ValueError("DigiKey client credentials not configured")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }

        try:
            response = await self._client.post(
                self.token_url,
                data=data,
                headers=headers
            )

            if response.status_code != 200:
                await log.aerror("digikey_auth_failed", status_code=response.status_code, response=response.text)
                raise Exception(f"Failed to authenticate with DigiKey: {response.status_code}")

            token_data = response.json()
            self._access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour if not specified

            if not self._access_token:
                raise Exception("No access token received from DigiKey")

            now = time.time()
            self._token_expiry = now + int(expires_in)
            self._token_issued_at = now

            await log.ainfo("digikey_token_refreshed", expires_in=expires_in)
            return self._access_token

        except httpx.RequestError as e:
            await log.aerror("digikey_network_error", error=str(e))
            raise Exception(f"Network error during DigiKey authentication: {e}")

    async def _make_authenticated_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        Make an authenticated request with automatic token refresh on 401 errors.
        """
        max_retries = 2
        for attempt in range(max_retries):
            try:
                if not self._is_token_valid():
                    self._clear_token_cache()

                token = await self._get_access_token()

                headers = kwargs.get('headers', {})
                headers['Authorization'] = f"Bearer {token}"
                headers['X-DIGIKEY-Client-Id'] = self.client_id
                kwargs['headers'] = headers

                response = await self._client.request(method, url, **kwargs)

                # If we get a 401, try refreshing the token
                if response.status_code == 401 and attempt < max_retries - 1:
                    await log.ainfo("digikey_token_expired_retry")
                    self._clear_token_cache()
                    continue

                return response

            except httpx.RequestError as e:
                if attempt < max_retries - 1:
                    await log.awarning("digikey_request_retry", attempt=attempt+1, error=str(e))
                    continue
                else:
                    await log.aerror("digikey_request_failed", error=str(e))
                    raise Exception(f"Network error during DigiKey API request: {e}")
        
        # Should be unreachable due to raise in loop, but for typing:
        raise Exception("Failed to make authenticated request")

    async def convert_to_digikey_filters(
        self,
        user_filters: dict,
        category_id: str
    ) -> list[dict]:
        """
        Convert user-friendly filters to Digi-Key ParametricFilter format.
        """
        # Load parameter mapping from JSON file
        mapping_file = Path(__file__).parent.parent / "data" / "digikey_parameter_mapping.json"
        # Reading file synchronously is fine as it's local and small
        # But ideally should be cached or async file read
        with open(mapping_file, 'r') as f:
            mapping_data = json.load(f)

        parameter_mappings = mapping_data.get("parameter_mappings", {})

        digikey_filters = []

        # Fetch filter values from DigiKey to get ValueIds for all filter types
        filter_response = await self.get_category_filter_options(category_id)
        parametric_filters_full = filter_response.get("ParametricFilters", [])
        
        for filter_alias, filter_value in user_filters.items():
            if filter_alias.startswith('_'):
                continue

            param_info = parameter_mappings.get(filter_alias)

            if not param_info:
                await log.awarning("digikey_unknown_filter", filter=filter_alias)
                continue

            param_id = param_info["parameter_id"]
            param_type = param_info["parameter_type"]

            if category_id not in param_info["categories"]:
                continue
            
            # Convert based on filter type
            if param_type == "UnitOfMeasure" and isinstance(filter_value, str):
                try:
                    parsed_filter = parse_user_range_filter(filter_value)
                    if parsed_filter:
                        min_val, max_val, unit = parsed_filter
                        param_data = next((pf for pf in parametric_filters_full if pf.get("ParameterId") == param_id), None)
    
                        if param_data:
                            all_values = param_data.get("FilterValues", [])
                            matching_values = []
                            for val_dict in all_values:
                                value_str = val_dict.get("ValueName", "")
                                value_id = val_dict.get("ValueId", "")
                                if not value_str or not value_id:
                                    continue

                                parsed = parse_physical_value(value_str)

                                if parsed:
                                    val, _ = parsed
                                    in_range = True
                                    if min_val is not None and val < min_val:
                                        in_range = False
                                    if max_val is not None and val > max_val:
                                        in_range = False

                                    if in_range:
                                        matching_values.append(str(value_id))

                            if matching_values:
                                digikey_filters.append({
                                    "ParameterId": param_id,
                                    "FilterValues": [{"Id": val} for val in matching_values]
                                })
                        else:
                             await log.awarning("digikey_no_filter_data", param_id=param_id)
                except Exception as e:
                    await log.aerror("digikey_parse_filter_error", error=str(e))

            else:
                if not isinstance(filter_value, list):
                    filter_value = [filter_value]

                if filter_value:
                    param_data = next((pf for pf in parametric_filters_full if pf.get("ParameterId") == param_id), None)

                    if param_data:
                        all_values = param_data.get("FilterValues", [])
                        
                        name_to_id = {
                            val_dict.get("ValueName", ""): str(val_dict.get("ValueId", ""))
                            for val_dict in all_values
                            if val_dict.get("ValueName") and val_dict.get("ValueId")
                        }

                        value_ids = []
                        for value_name in filter_value:
                            if value_name in name_to_id:
                                value_ids.append(name_to_id[value_name])

                        if value_ids:
                            digikey_filters.append({
                                "ParameterId": param_id,
                                "FilterValues": [{"Id": vid} for vid in value_ids]
                            })

        return digikey_filters

    async def search_parts(self, keyword: str, limit: int = 10, offset: int = 0) -> dict:
        url = f"{self.base_url}/Search/v3/Products/Keyword"

        payload = {
            "Keywords": keyword,
            "Limit": limit,
            "Offset": offset,
            "SearchOptions": [],
            "ExcludeMarketPlaceProducts": False
        }

        response = await self._make_authenticated_request(
            "POST",
            url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            json=payload
        )

        if response.status_code != 200:
             await log.aerror("digikey_search_failed", status=response.status_code)
             raise Exception(f"DigiKey search failed: {response.status_code}")

        return response.json()

    async def get_part_details(self, part_number: str) -> dict:
        url = f"{self.base_url}/Search/v3/Products/{part_number}"

        response = await self._make_authenticated_request(
            "GET",
            url,
            headers={"Accept": "application/json"}
        )

        if response.status_code != 200:
             raise Exception(f"DigiKey part details failed: {response.status_code}")

        return response.json()

    async def search_chips(
        self,
        keywords: str,
        category_id: str | None = None,
        parametric_filters: list[dict[str, Any]] | None = None,
        manufacturer_ids: list[str] | None = None,
        search_options: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
        sort_field: str | None = None,
        sort_order: str | None = "Ascending"
    ) -> dict:
        request_data: dict[str, Any] = {
            "Keywords": keywords,
            "Limit": limit,
            "Offset": offset
        }

        if any([category_id, parametric_filters, manufacturer_ids, search_options]):
            filter_request: dict[str, Any] = {}

            if manufacturer_ids:
                filter_request["ManufacturerFilter"] = [{"Id": mid} for mid in manufacturer_ids]

            if category_id:
                filter_request["CategoryFilter"] = [{"Id": category_id}]

            if search_options:
                filter_request["SearchOptions"] = search_options

            if parametric_filters and category_id:
                filter_request["ParameterFilterRequest"] = {
                    "CategoryFilter": {"Id": category_id},
                    "ParameterFilters": parametric_filters
                }

            request_data["FilterOptionsRequest"] = filter_request

        if sort_field:
            request_data["SortOptions"] = {
                "Field": sort_field,
                "SortOrder": sort_order
            }

        url = f"{self.base_url}/products/v4/search/keyword"

        response = await self._make_authenticated_request(
            "POST",
            url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            json=request_data
        )

        if response.status_code != 200:
            await log.aerror("digikey_parametric_search_failed", status=response.status_code)
            raise Exception(f"DigiKey parametric search failed: {response.status_code}")

        return response.json()

    async def health_check(self) -> bool:
        try:
            url = f"{self.base_url}/products/v4/search/categories"
            response = await self._make_authenticated_request(
                "GET",
                url,
                headers={"Accept": "application/json"},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            await log.aerror("digikey_health_check_failed", error=str(e))
            return False

    async def get_categories(self) -> list[ChipCategory]:
        url = f"{self.base_url}/products/v4/search/categories"

        response = await self._make_authenticated_request(
            "GET",
            url,
            headers={"Accept": "application/json"}
        )

        if response.status_code != 200:
             raise Exception(f"DigiKey categories search failed: {response.status_code}")

        all_categories = response.json().get("Categories", [])

        result_categories = []
        for cat in all_categories:
            cat_name = cat.get("Name", "")
            children = cat.get("Children", [])

            if not children:
                continue

            subcategories = []
            for child in children:
                child_id = str(child.get("CategoryId", ""))
                child_name = child.get("Name", "")
                child_count = child.get("ProductCount", 0)

                subcategories.append(ChipSubcategoryInfo(
                    name=child_name,
                    component_count=child_count,
                    category_id=child_id
                ))

            subcategories.sort(key=lambda x: x.component_count, reverse=True)

            result_categories.append(ChipCategory(
                name=cat_name,
                subcategories=subcategories
            ))

        result_categories.sort(key=lambda x: x.name)
        return result_categories

    async def get_category_filter_options(self, category_id: str) -> dict[int, str]:
        request_data = {
            "Keywords": "",
            "Limit": 1,
            "FilterOptionsRequest": {
                "CategoryFilter": [{"Id": category_id}]
            }
        }

        url = f"{self.base_url}/products/v4/search/keyword"

        response = await self._make_authenticated_request(
            "POST",
            url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            json=request_data
        )

        if response.status_code != 200:
            raise Exception(f"DigiKey filter retrieval failed: {response.status_code}")

        return response.json().get('FilterOptions', {})

    async def get_category_filters(self, category_id: str) -> dict[str, ChipFilterPhysicalUnitRange | ChipFilterMultichoice]:
        filter_options = await self.get_category_filter_options(category_id)
        parametric_filters = filter_options.get("ParametricFilters", [])
        if not parametric_filters:
            return {}

        filter_configs = {}
        for param_filter in parametric_filters:
            param_name = param_filter.get("ParameterName", "")
            param_type = param_filter.get("ParameterType", "")
            filter_values = param_filter.get("FilterValues", [])

            if not param_name or not filter_values:
                continue

            alias = generate_python_alias(param_name)

            product_count = 0
            unique_values_set = set()

            for val_dict in filter_values:
                value_name = val_dict.get("ValueName", "")
                if value_name and value_name != '-':
                    unique_values_set.add(value_name)
                    product_count += val_dict.get("ProductCount", 0)

            if param_type == 'UnitOfMeasure':
                units_set = set()
                for val_dict in filter_values:  
                    value_name = val_dict.get("ValueName", "")
                    if not value_name or value_name == '-':
                        continue
                    
                    parts = value_name.split()
                    if len(parts) >= 2:
                        units_set.add(parts[1])

                available_units = list(units_set)

                SI_PREFIX_ORDER = ['p', 'n', 'u', 'µ', 'm', '', 'k', 'K', 'M', 'G', 'T']  
                def get_prefix_order(unit: str) -> int:
                    for i, prefix in enumerate(SI_PREFIX_ORDER):
                        if unit.startswith(prefix):
                            return i
                    return len(SI_PREFIX_ORDER)

                available_units.sort(key=get_prefix_order)

                if available_units:
                    filter_configs[alias] = ChipFilterPhysicalUnitRange(
                        type='physical_unit_range',
                        name=param_name,
                        alias=alias,
                        available_units=available_units,
                        product_count=product_count,
                        unique_value_count=len(unique_values_set)
                    )
            else:
                available_values = sorted([
                    ChipFilterMultichoiceValue(
                        value=val_dict.get("ValueName", ""),
                        num_chips_with_value=val_dict.get("ProductCount", 0)
                    )
                    for val_dict in filter_values
                    if val_dict.get("ValueName") and val_dict.get("ValueName") != '-'
                ], key=lambda x: x.num_chips_with_value, reverse=True)
                
                if available_values:
                    filter_configs[alias] = ChipFilterMultichoice(
                        type='multichoice',
                        name=param_name,
                        alias=alias,
                        default=available_values[0].value,
                        available_values=available_values,
                        product_count=product_count,
                        unique_value_count=len(unique_values_set)
                    )

        return filter_configs
