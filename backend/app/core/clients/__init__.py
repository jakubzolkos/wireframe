from .digikey import DigiKeyClient
from .ul import UltraLibrarianClient


_ul_client: UltraLibrarianClient | None = None
_digikey_client: DigiKeyClient | None = None


def get_ultralibrarian_client() -> UltraLibrarianClient:
    """Get the UltraLibrarian client instance"""
    global _ul_client
    if _ul_client is None:
        _ul_client = UltraLibrarianClient()
    return _ul_client

def _get_digikey_client_internal() -> DigiKeyClient:
    """Internal function to get the DigiKey client instance without health check"""
    global _digikey_client
    if _digikey_client is None:
        _digikey_client = DigiKeyClient()
    return _digikey_client

def get_digikey_client() -> DigiKeyClient:
    """
    Get the DigiKey client instance.
    """
    return _get_digikey_client_internal()
