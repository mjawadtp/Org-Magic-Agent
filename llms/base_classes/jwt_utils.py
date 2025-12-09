import os
import time
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class JWTTokenManager:
    _access_token: Optional[str] = None
    _access_token_expiry: Optional[float] = None

    @classmethod
    def get_jwt_token(cls) -> str:
        if (
            cls._access_token
            and cls._access_token_expiry
            and time.time() < cls._access_token_expiry - 120
        ):
            return cls._access_token

        org_domain = os.environ.get("EINSTEIN_ORG_DOMAIN_URL")
        client_id = os.environ.get("EINSTEIN_ORG_CLIENT_ID")
        client_secret = os.environ.get("EINSTEIN_ORG_CLIENT_SECRET")
        token_url = f"https://{org_domain}/services/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            response = requests.post(token_url, data=payload, headers=headers, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 1800)
            if not access_token:
                raise ValueError(f"No access_token in response: {token_data}")
            cls._access_token = access_token
            cls._access_token_expiry = time.time() + int(expires_in)
            return access_token
        except Exception as e:
            logger.error(f"Failed to fetch JWT token: {e}")
            raise 