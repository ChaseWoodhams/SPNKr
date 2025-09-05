#!/usr/bin/env python3
"""Script to get service record for a Halo Infinite player."""

import asyncio
import os
import sys
from aiohttp import ClientSession
from spnkr import AzureApp, refresh_player_tokens, HaloInfiniteClient
from dotenv import load_dotenv

# Load env
load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"), override=False, encoding="utf-8")


def _norm(value: str | None, default: str = "") -> str:
    v = value if value is not None else default
    v = v.strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1].strip()
    return v

# Azure app credentials
CLIENT_ID = _norm(os.getenv("SPNKR_CLIENT_ID"))
CLIENT_SECRET = _norm(os.getenv("SPNKR_CLIENT_SECRET"))
REDIRECT_URI = _norm(os.getenv("SPNKR_REDIRECT_URI"), "https://localhost")
REFRESH_TOKEN = _norm(os.getenv("SPNKR_REFRESH_TOKEN"))

# Default gamertag
DEFAULT_GAMERTAG = _norm(os.getenv("DEFAULT_GAMERTAG"), "itsmrpixle")


def _require_env(var_name: str, value: str) -> None:
    if not value:
        raise RuntimeError(f"Missing required environment variable: {var_name}")


async def get_service_record(gamertag: str = DEFAULT_GAMERTAG):
    """Get and display service record for a player."""
    print(f"🎮 Getting Service Record for: {gamertag}")
    print("=" * 50)

    # Validate env
    _require_env("SPNKR_CLIENT_ID", CLIENT_ID)
    _require_env("SPNKR_CLIENT_SECRET", CLIENT_SECRET)
    _require_env("SPNKR_REFRESH_TOKEN", REFRESH_TOKEN)

    # Create Azure app configuration
    app = AzureApp(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)

    async with ClientSession() as session:
        try:
            # Refresh tokens to get spartan and clearance tokens
            print("🔐 Refreshing authentication tokens...")
            player = await refresh_player_tokens(session, app, REFRESH_TOKEN)
            print(f"✅ Authenticated as: {player.gamertag} (XUID: {player.player_id})")
            print()

            # Create SPNKr client
            client = HaloInfiniteClient(
                session=session,
                spartan_token=player.spartan_token.token,
                clearance_token=player.clearance_token.token
            )

            # Get user profile to convert gamertag to XUID
            print(f"🔍 Looking up player: {gamertag}")
            user_response = await client.profile.get_user_by_gamertag(gamertag)
            user = await user_response.parse()
            print(f"✅ Found player: {user.gamertag} (XUID: {user.xuid})")
            print()

            # Get service record (matchmade games)
            print("📊 Fetching service record...")
            service_record_response = await client.stats.get_service_record(
                player=user.xuid,
                match_type="matchmade"
            )
            service_record = await service_record_response.parse()

            # Display service record information
            print("🏆 SERVICE RECORD")
            print("-" * 40)
            print(f"Player: {gamertag}")
            print(f"Total Matches: {service_record.matches_completed}")
            print(f"Wins: {service_record.wins}")
            print(f"Losses: {service_record.losses}")
            print(f"Ties: {service_record.ties}")

            if service_record.matches_completed > 0:
                win_rate = (service_record.wins / service_record.matches_completed) * 100
                print(f"Win Rate: {win_rate:.1f}%")

            print(f"Time Played: {service_record.time_played}")
            print()

            # Core stats
            core_stats = service_record.core_stats
            print("⚔️  CORE STATISTICS")
            print("-" * 40)
            print(f"Kills: {core_stats.kills}")
            print(f"Deaths: {core_stats.deaths}")
            print(f"Assists: {core_stats.assists}")

            if core_stats.deaths > 0:
                kd_ratio = core_stats.kills / core_stats.deaths
                print(f"K/D Ratio: {kd_ratio:.2f}")

            if core_stats.shots_fired > 0:
                accuracy = (core_stats.shots_hit / core_stats.shots_fired) * 100
                print(f"Accuracy: {accuracy:.1f}% ({core_stats.shots_hit}/{core_stats.shots_fired})")

            # Check available attributes and display them
            if hasattr(core_stats, 'headshots'):
                print(f"Headshots: {core_stats.headshots}")
            if hasattr(core_stats, 'medals'):
                print(f"Medals: {core_stats.medals}")
            if hasattr(core_stats, 'damage_dealt'):
                print(f"Damage Dealt: {core_stats.damage_dealt:,}")
            if hasattr(core_stats, 'damage_taken'):
                print(f"Damage Taken: {core_stats.damage_taken:,}")

            print(f"Rounds Won: {core_stats.rounds_won}")
            print(f"Rounds Lost: {core_stats.rounds_lost}")
            print(f"Rounds Tied: {core_stats.rounds_tied}")
            print()

            # PvP stats if available
            if service_record.pvp_stats:
                pvp_stats = service_record.pvp_stats
                print("🎯 PVP STATISTICS")
                print("-" * 40)
                print(f"Kills: {pvp_stats.kills}")
                print(f"Deaths: {pvp_stats.deaths}")
                if pvp_stats.deaths > 0:
                    pvp_kd = pvp_stats.kills / pvp_stats.deaths
                    print(f"PvP K/D: {pvp_kd:.2f}")
                print()

            print("✅ Service record retrieved successfully!")

        except Exception as e:
            print(f"❌ Error: {e}")
            print(f"Error type: {type(e).__name__}")
            return 1

    return 0


async def main():
    """Main function."""
    # Check if gamertag was provided as command line argument
    gamertag = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GAMERTAG

    if gamertag != DEFAULT_GAMERTAG:
        print(f"Using provided gamertag: {gamertag}")
    else:
        print(f"Using default gamertag: {gamertag}")
        print("(You can provide a different gamertag as a command line argument)")
    print()

    return await get_service_record(gamertag)


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
