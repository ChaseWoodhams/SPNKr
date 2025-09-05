#!/usr/bin/env python3
"""Flask web server for Halo Infinite Service Record frontend."""

import asyncio
import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from aiohttp import ClientSession
from spnkr import AzureApp, refresh_player_tokens, HaloInfiniteClient
from dotenv import load_dotenv

# Load environment variables from .env if present (utf-8 to avoid encoding issues)
load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"), override=False, encoding="utf-8")


def _normalize_env(value: str | None, default: str = "") -> str:
    v = value if value is not None else default
    v = v.strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1].strip()
    return v


# Azure app credentials from environment (normalized)
CLIENT_ID = _normalize_env(os.getenv("SPNKR_CLIENT_ID"))
CLIENT_SECRET = _normalize_env(os.getenv("SPNKR_CLIENT_SECRET"))
REDIRECT_URI = _normalize_env(os.getenv("SPNKR_REDIRECT_URI"), "https://localhost")
REFRESH_TOKEN = _normalize_env(os.getenv("SPNKR_REFRESH_TOKEN"))

# Optional server config
PORT = int(_normalize_env(os.getenv("PORT"), "5000") or "5000")
FLASK_DEBUG = _normalize_env(os.getenv("FLASK_DEBUG"), "true").lower() in ("1", "true", "yes")
CORS_ORIGINS = _normalize_env(os.getenv("CORS_ORIGINS"))  # e.g. "http://localhost:5173,http://localhost:3000"

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": CORS_ORIGINS.split(",") if CORS_ORIGINS else "*"}})

# Cache for tokens to avoid re-authenticating on every request
_cached_tokens = None


def _require_env(var_name: str, value: str) -> None:
    if not value:
        raise RuntimeError(f"Missing required environment variable: {var_name}")


async def get_authenticated_client():
    """Get an authenticated SPNKr client."""
    global _cached_tokens

    # Validate env
    _require_env("SPNKR_CLIENT_ID", CLIENT_ID)
    _require_env("SPNKR_CLIENT_SECRET", CLIENT_SECRET)
    _require_env("SPNKR_REFRESH_TOKEN", REFRESH_TOKEN)

    app_config = AzureApp(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
    session = ClientSession()

    # Get fresh tokens
    player = await refresh_player_tokens(session, app_config, REFRESH_TOKEN)

    # Cache tokens for reuse
    _cached_tokens = {
        'spartan_token': player.spartan_token.token,
        'clearance_token': player.clearance_token.token,
        'player_info': {
            'gamertag': player.gamertag,
            'xuid': player.player_id
        }
    }

    # Create and return client
    client = HaloInfiniteClient(
        session=session,
        spartan_token=player.spartan_token.token,
        clearance_token=player.clearance_token.token
    )

    return client, session


async def get_service_record_async(gamertag):
    """Async function to get service record."""
    client, session = await get_authenticated_client()

    try:
        # Get user profile
        user_response = await client.profile.get_user_by_gamertag(gamertag)
        user = await user_response.parse()

        # Get service record
        service_record_response = await client.stats.get_service_record(
            player=user.xuid,
            match_type="matchmade"
        )
        service_record = await service_record_response.parse()

        # Get CSR data for common ranked playlists
        csr_data = await get_csr_data(client, user.xuid)

        # Convert to JSON-serializable format
        result = {
            'player': {
                'gamertag': user.gamertag,
                'xuid': user.xuid
            },
            'service_record': {
                'matches_completed': service_record.matches_completed,
                'wins': service_record.wins,
                'losses': service_record.losses,
                'ties': service_record.ties,
                'time_played': str(service_record.time_played),
                'core_stats': {
                    'kills': service_record.core_stats.kills,
                    'deaths': service_record.core_stats.deaths,
                    'assists': service_record.core_stats.assists,
                    'shots_fired': service_record.core_stats.shots_fired,
                    'shots_hit': service_record.core_stats.shots_hit,
                    'damage_dealt': service_record.core_stats.damage_dealt,
                    'damage_taken': service_record.core_stats.damage_taken,
                    'rounds_won': service_record.core_stats.rounds_won,
                    'rounds_lost': service_record.core_stats.rounds_lost,
                    'rounds_tied': service_record.core_stats.rounds_tied,
                },
                'pvp_stats': None
            },
            'csr_data': csr_data
        }

        # Add PvP stats if available
        if service_record.pvp_stats:
            result['service_record']['pvp_stats'] = {
                'kills': service_record.pvp_stats.kills,
                'deaths': service_record.pvp_stats.deaths,
            }

        return result

    except Exception as e:
        raise Exception(f"Failed to get service record: {str(e)}")
    finally:
        # Always close the session
        await session.close()


async def get_csr_data(client, xuid):
    """Get CSR data for common ranked playlists."""
    # Common ranked playlist IDs (these are typical Halo Infinite ranked playlists)
    ranked_playlists = {
        'ranked_arena': 'edfef3ac-9cbe-4fa2-b949-8f29deafd483',  # Ranked Arena
        'ranked_slayer': 'f7f30787-f607-436b-bdec-44c65bc2ecef',  # Ranked Slayer  
        'ranked_crossplay': 'c98949c6-f018-4e54-9243-a5b9c0246da2',  # Ranked Crossplay
    }

    csr_results = {}

    for playlist_name, playlist_id in ranked_playlists.items():
        try:
            csr_response = await client.skill.get_playlist_csr(
                playlist_id=playlist_id,
                xuids=[xuid]
            )
            csr_data = await csr_response.parse()

            if csr_data.value and len(csr_data.value) > 0:
                player_csr = csr_data.value[0]
                if hasattr(player_csr, 'result') and player_csr.result:
                    result = player_csr.result
                    csr_results[playlist_name] = {
                        'current': format_csr_container(result.current),
                        'season_max': format_csr_container(result.season_max),
                        'all_time_max': format_csr_container(result.all_time_max),
                    }
        except Exception as e:
            # If playlist doesn't exist or player hasn't played it, skip
            print(f"Could not get CSR for {playlist_name}: {e}")
            continue

    return csr_results


def format_csr_container(csr_container):
    """Format CSR container data for JSON serialization."""
    if not csr_container:
        return None

    return {
        'value': csr_container.value,
        'tier': csr_container.tier.value if hasattr(csr_container.tier, 'value') else str(csr_container.tier),
        'sub_tier': csr_container.sub_tier.value if hasattr(csr_container.sub_tier, 'value') else str(csr_container.sub_tier),
        'tier_start': csr_container.tier_start,
        'next_tier': csr_container.next_tier.value if hasattr(csr_container.next_tier, 'value') else str(csr_container.next_tier),
        'next_tier_start': csr_container.next_tier_start,
        'measurement_matches_remaining': csr_container.measurement_matches_remaining,
        'formatted_rank': format_rank_display(csr_container)
    }


def format_rank_display(csr_container):
    """Format rank for display (e.g., 'Diamond IV - 1250 CSR')."""
    if not csr_container:
        return "Unranked"

    tier = csr_container.tier.value if hasattr(csr_container.tier, 'value') else str(csr_container.tier)

    # Handle Onyx (no sub-tiers)
    if tier.lower() == 'onyx':
        return f"Onyx - {csr_container.value} CSR"

    # Handle other tiers with sub-tiers
    sub_tier_map = {0: "I", 1: "II", 2: "III", 3: "IV", 4: "V", 5: "VI"}
    sub_tier_num = csr_container.sub_tier.value if hasattr(csr_container.sub_tier, 'value') else csr_container.sub_tier
    sub_tier_roman = sub_tier_map.get(sub_tier_num, str(sub_tier_num + 1))

    return f"{tier} {sub_tier_roman} - {csr_container.value} CSR"


@app.route('/')
def index():
    """Serve the main HTML page."""
    return send_from_directory('web', 'index.html')


@app.route('/favicon.ico')
def favicon():
    """Return a simple favicon response."""
    return '', 204


@app.route('/<path:filename>')
def static_files(filename):
    """Serve static files (CSS, JS)."""
    return send_from_directory('web', filename)


@app.route('/api/service-record', methods=['POST'])
def api_service_record():
    """API endpoint to get service record."""
    try:
        data = request.get_json()
        if not data or 'gamertag' not in data:
            return jsonify({'error': 'Gamertag is required'}), 400

        gamertag = data['gamertag'].strip()
        if not gamertag:
            return jsonify({'error': 'Gamertag cannot be empty'}), 400

        # Run the async function in a new event loop
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(get_service_record_async(gamertag))
            loop.close()

            return jsonify(result)

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    except Exception as e:
        return jsonify({'error': f'Invalid request: {str(e)}'}), 400


@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'message': 'Halo Infinite Service Record API is running'
    })


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    print("Starting Halo Infinite Service Record Web Server...")
    print(f"Frontend: http://localhost:{PORT}")
    print(f"API:      http://localhost:{PORT}/api/service-record")
    print(f"Health:   http://localhost:{PORT}/api/health")
    print()
    print("Press Ctrl+C to stop the server")

    app.run(debug=FLASK_DEBUG, host='0.0.0.0', port=PORT)
