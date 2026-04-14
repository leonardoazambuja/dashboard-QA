from dotenv import load_dotenv
import os

load_dotenv()

AZDO_ORG = os.getenv("AZDO_ORG")
AZDO_PROJECT = os.getenv("AZDO_PROJECT")
AZDO_PAT = os.getenv("AZDO_PAT")
AZDO_API_VERSION = os.getenv("AZDO_API_VERSION", "7.1")
DEFAULT_DAYS_BACK = int(os.getenv("DEFAULT_DAYS_BACK", "15"))

BASE_TEST_URL = f"https://dev.azure.com/{AZDO_ORG}/{AZDO_PROJECT}/_apis/test"