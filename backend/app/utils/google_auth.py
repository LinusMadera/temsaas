from urllib.parse import urlencode

import requests
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
from fastapi import HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token


def verify_google_token(token: str):
    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Wrong issuer.")
        return idinfo
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid token: {str(e)}")


def get_google_auth_url(redirect_uri: str):
    """Generate Google OAuth 2.0 authorization URL"""
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": redirect_uri,
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{base_url}?{urlencode(params)}"


def get_google_token(code: str, redirect_uri: str):
    """Exchange authorization code for access token"""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        token_data = response.json()
        return token_data["id_token"]
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to retrieve token: {str(e)}")
