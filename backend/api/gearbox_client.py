import io
import zipfile

import requests
from django.conf import settings


def get_access_token():
    response = requests.post(
        settings.FENCE_TOKEN_URL,
        data={"grant_type": "client_credentials", "scope": "openid user"},
        auth=(settings.FENCE_CLIENT_ID, settings.FENCE_CLIENT_SECRET),
    )
    response.raise_for_status()
    return response.json()["access_token"]


def submit_to_gearbox(jsonl_content: bytes, filename: str = "annotations.jsonl"):
    token = get_access_token()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(filename, jsonl_content)
    zip_buffer.seek(0)

    response = requests.post(
        settings.GEARBOX_RAW_CRITERIA_URL,
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("annotations.zip", zip_buffer, "application/zip")},
    )
    response.raise_for_status()
    return response
