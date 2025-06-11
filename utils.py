import requests
import os

IMEI_API_KEY = os.getenv("IMEI_API_KEY")
IMEI_API_URL = os.getenv("IMEI_API_URL")

def check_imei(imei: str, service: int = 4):
    data = {
        "service": service,
        "imei": imei,
        "key": IMEI_API_KEY
    }
    try:
        response = requests.post(IMEI_API_URL, data=data, timeout=60)
        if response.status_code != 200:
            return {"success": False, "error": f"HTTP Error: {response.status_code}"}
        result = response.json()
        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Unknown error")}
        return {"success": True, "data": result.get("object", {})}
    except Exception as e:
        return {"success": False, "error": str(e)}
