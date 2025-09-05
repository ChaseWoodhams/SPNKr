#!/usr/bin/env python3
"""Simple script to obtain an OAuth2 refresh token for SPNKr authentication."""

import asyncio
import os
from aiohttp import ClientSession
from spnkr import AzureApp, authenticate_player
from dotenv import load_dotenv

load_dotenv()

# Azure app credentials
CLIENT_ID = os.getenv("SPNKR_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("SPNKR_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("SPNKR_REDIRECT_URI", "https://localhost")  # Must match your Azure app redirect URI


def _require_env(var_name: str, value: str) -> None:
    if not value:
        raise RuntimeError(f"Missing required environment variable: {var_name}")


async def main():
    """Main authentication flow to get refresh token."""
    print("🎮 SPNKr Authentication - Getting Refresh Token")
    print("=" * 50)

    _require_env("SPNKR_CLIENT_ID", CLIENT_ID)
    _require_env("SPNKR_CLIENT_SECRET", CLIENT_SECRET)

    # Create Azure app configuration
    app = AzureApp(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)

    print(f"Client ID: {CLIENT_ID}")
    print(f"Redirect URI: {REDIRECT_URI}")
    print()

    async with ClientSession() as session:
        try:
            print("🔐 Starting authentication flow...")
            print("This will prompt you to authenticate via Xbox Live.")
            print()

            # Perform the authentication
            refresh_token = await authenticate_player(session, app)

            print("✅ Authentication successful!")
            print()
            print("🔑 Your refresh token:")
            print("-" * 60)
            print(refresh_token)
            print("-" * 60)
            print()
            print("💾 Save this refresh token securely!")
            print("You can use it with SPNKr to avoid repeated authentication.")

        except KeyboardInterrupt:
            print("\n⏹️  Authentication cancelled by user.")
            return 1
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            print(f"Error type: {type(e).__name__}")
            print()
            print("Common issues:")
            print("- Make sure you have an active internet connection")
            print("- Check that your Azure app is configured correctly")
            print("- Ensure the redirect URI matches your app configuration")
            print("- Make sure you complete the authentication in your browser")
            return 1

    return 0


if __name__ == "__main__":
    print("Script starting...")
    try:
        exit_code = asyncio.run(main())
        print(f"Script completed with exit code: {exit_code}")
        exit(exit_code)
    except Exception as e:
        print(f"Script failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
