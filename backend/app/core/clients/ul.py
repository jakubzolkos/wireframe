import base64
import os
import tempfile
import time
from typing import Optional
import zipfile

import httpx
import structlog
from app.core.clients.cache import cache_returned_dataclass_to_disk
from app.core.config import settings
from autopcb.datatypes.pcb import Footprint
from autopcb.datatypes.schematics import SymbolLibrary
from autopcb.models import ParsedChip

log = structlog.get_logger()


class UltraLibrarianClient:
    """Async Client for interacting with UltraLibrarian API"""
    
    def __init__(self):
        self.client_id = settings.UL_CLIENT_ID
        self.client_secret = settings.UL_CLIENT_SECRET
        self.token_url = "https://sso.ultralibrarian.com/connect/token"
        self.base_url = "https://api.ultralibrarian.com/api/v1"
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[float] = None
        self._token_issued_at: Optional[float] = None
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
        return self._token_expiry > now + 30
        
    async def _get_access_token(self) -> str:
        """Get OAuth2 access token, caching it for reuse and refreshing if expired."""
        if self._is_token_valid():
            return self._access_token
            
        if not self.client_id or not self.client_secret:
            raise ValueError("UltraLibrarian client credentials not configured")
            
        authorization = base64.b64encode(
            bytes(f"{self.client_id}:{self.client_secret}", "ISO-8859-1")
        ).decode("ascii")
        
        headers = {
            "Authorization": f"Basic {authorization}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            response = await self._client.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "scope": "export parts"
                },
                headers=headers
            )
            
            if response.status_code != 200:
                await log.aerror("ul_auth_failed", status_code=response.status_code, response=response.text)
                raise Exception(f"Failed to authenticate with UltraLibrarian: {response.status_code}")
            
            token_data = response.json()
            self._access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)
            
            if not self._access_token:
                raise Exception("No access token from UltraLibrarian")
                
            now = time.time()
            self._token_expiry = now + int(expires_in)
            self._token_issued_at = now
            
            await log.ainfo("ul_token_refreshed", expires_in=expires_in)
            return self._access_token
            
        except httpx.RequestError as e:
            await log.aerror("ul_network_error", error=str(e))
            raise Exception(f"Network error during UltraLibrarian authentication: {e}")

    async def _make_authenticated_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make an authenticated request with automatic token refresh on 401 errors."""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                if not self._is_token_valid():
                    self._clear_token_cache()
                    
                token = await self._get_access_token()
                
                headers = kwargs.get('headers', {})
                headers['Authorization'] = f"Bearer {token}"
                kwargs['headers'] = headers
                
                response = await self._client.request(method, url, **kwargs)

                if response.status_code == 401 and attempt < max_retries - 1:
                    www_auth = response.headers.get("WWW-Authenticate", "")
                    if "Bearer" in www_auth:
                        await log.awarning("ul_token_expired_retry")
                        self._clear_token_cache()
                        continue
                    else:
                        return response

                return response
                
            except httpx.RequestError as e:
                if attempt < max_retries - 1:
                    await log.awarning("ul_request_retry", attempt=attempt+1, error=str(e))
                    continue
                else:
                    await log.aerror("ul_request_failed", error=str(e))
                    raise Exception(f"Network error during UltraLibrarian API request: {e}")
        
        raise Exception("Failed to make authenticated request")
        
    async def search_chips(self, query: str) -> list[dict]:
        """Search for parts by query string"""
        response = await self._make_authenticated_request(
            "GET",
            f"{self.base_url}/parts/search?q={query}&exact_only=false",
            headers={"accept": "application/json"}
        )

        if response.status_code != 200:
            await log.aerror("ul_search_failed", status_code=response.status_code, response=response.text)
            raise Exception(f"Search failed: {response.status_code}")

        data = response.json()
        return data.get("results", [])

    async def search_chips_by_manufacturer_info(self, parts: list[dict[str, str]], eda_models_available: bool = True) -> dict[str, dict]:
        """Batch search for multiple parts by MPN and manufacturer."""
        response = await self._make_authenticated_request(
            "POST",
            f"{self.base_url}/parts/findparts",
            headers={
                "accept": "application/json",
                "Content-Type": "application/json"
            },
            json={"parts": parts}
        )

        if response.status_code != 200:
            await log.aerror("ul_batch_search_failed", status_code=response.status_code, response=response.text)
            raise Exception(f"Batch search failed: {response.status_code}")

        data = response.json()

        mpn_to_result = {}
        for result in data:
            mpn = result.get("mpn", "")
            part_response = result.get("part_response")
            if mpn and part_response and (part_data := part_response.get("part_data")):
                if eda_models_available:
                    if part_data.get("symbol_available") and part_data.get("footprint_available"):
                        mpn_to_result[mpn] = result
                else:
                    mpn_to_result[mpn] = result

        return mpn_to_result
    
    async def get_symbol_preview(self, uid: str) -> str:
        """Get symbol preview for a part by UID"""
        response = await self._make_authenticated_request(
            "GET",
            f"{self.base_url}/parts/preview/symbol?uid={uid}",
            headers={"accept": "application/json"}
        )
        
        if response.status_code != 200:
            await log.aerror("ul_symbol_preview_failed", status_code=response.status_code, response=response.text)
            raise Exception(f"Symbol preview failed: {response.status_code}")

        return response.json()
    
    async def get_footprint_preview(self, uid: str) -> str:
        """Get footprint preview for a part by UID"""
        response = await self._make_authenticated_request(
            "GET",
            f"{self.base_url}/parts/preview/footprint?uid={uid}",
            headers={"accept": "application/json"}
        )

        if response.status_code != 200:
            await log.aerror("ul_footprint_preview_failed", status_code=response.status_code, response=response.text)
            raise Exception(f"Footprint preview failed: {response.status_code}")
        
        return response.json()
    
    async def get_3d_preview(self, uid: str) -> Optional[str]:
        """Get 3D preview for a part by UID"""
        response = await self._make_authenticated_request(
            "GET",
            f"{self.base_url}/parts/preview/threed?uid={uid}",
            headers={"accept": "application/json"}
        )
        if response.status_code != 200:
            return None
        
        return response.json()

    @cache_returned_dataclass_to_disk
    async def get_chip(self, uid: str) -> ParsedChip:
        """Get KiCad symbol file path from UltraLibrarian export endpoint"""
        response = await self._make_authenticated_request(
            "POST",
            f"{self.base_url}/export",
            headers={
                "accept": "application/zip",
                "Content-Type": "application/json"
            },
            json={
                "uid": uid,
                "export_format_id": 42
            },
            timeout=60.0
        )

        if response.status_code != 200:
            await log.aerror("ul_export_failed", status_code=response.status_code, response=response.text)
            raise Exception(f"Export failed: {response.status_code}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "exports.zip")
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            kicad_dir = os.path.join(temp_dir, "KiCADv6")
            if not os.path.exists(kicad_dir):
                raise Exception("No 'KiCADv6' directory found in exports")

            kicad_sym_files = [f for f in os.listdir(kicad_dir) if f.endswith('.kicad_sym')]
            if not kicad_sym_files:
                raise Exception("No .kicad_sym file found in KiCADv6 directory")

            if len(kicad_sym_files) > 1:
                await log.awarning("ul_multiple_symbol_files", files=kicad_sym_files)

            chip_file_path = os.path.join(kicad_dir, kicad_sym_files[0])
            lib = SymbolLibrary.from_file(chip_file_path)
            if not lib.symbols:
                raise Exception("No symbols found in the KiCad symbol file")

            chip_symbol = lib.symbols[0]

            footprint_dir = os.path.join(kicad_dir, "footprints.pretty")
            if not os.path.exists(footprint_dir):
                raise Exception("No 'footprints.pretty' directory found in KiCADv6")

            kicad_mod_files = [f for f in os.listdir(footprint_dir) if f.endswith('.kicad_mod')]
            if not kicad_mod_files:
                raise Exception("No .kicad_mod file found in footprints.pretty directory")

            if len(kicad_mod_files) > 1:
                await log.awarning("ul_multiple_footprint_files", files=kicad_mod_files)

            footprint_file_path = os.path.join(footprint_dir, kicad_mod_files[0])
            footprint = Footprint.from_file(footprint_file_path)

            return ParsedChip(
                symbol=chip_symbol,
                footprint=footprint
            )
