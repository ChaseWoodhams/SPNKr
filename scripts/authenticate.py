"""Perform the initial authentication flow to obtain an OAuth2 refresh token."""

import asyncio
import os

import dotenv
from aiohttp import ClientSession

from spnkr import AzureApp, authenticate_player

dotenv.load_dotenv()

CLIENT_ID = os.environ.get("SPNKR_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("SPNKR_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("SPNKR_REDIRECT_URI", "https://localhost")


async def main() -> None:
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError("SPNKR_CLIENT_ID and SPNKR_CLIENT_SECRET must be set in environment")

    app = AzureApp(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)

    async with ClientSession() as session:
        refresh_token = await authenticate_player(session, app)
    print(f"Your refresh token is:\n{refresh_token}")


if __name__ == "__main__":
    asyncio.run(main())
