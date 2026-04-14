import requests
from requests.auth import HTTPBasicAuth
from src.config import AZDO_PAT

AUTH = HTTPBasicAuth("", AZDO_PAT)

def get_json(url: str, params: dict | None = None) -> dict:
    response = requests.get(url, auth=AUTH, params=params, timeout=30)
    response.raise_for_status()
    return response.json()

def get_json_with_headers(url: str, params: dict | None = None):
    response = requests.get(url, auth=AUTH, params=params, timeout=30)
    response.raise_for_status()
    return response.json(), response.headers