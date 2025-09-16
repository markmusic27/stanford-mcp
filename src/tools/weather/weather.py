import httpx
from typing import Any
import mcp.types as types

from tools.registry import register_tool 

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"


# Helper functions
async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""

def format_forecast(forecast_data: dict) -> str:
    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)

async def get_alerts(state: str) -> list[str]:
    """Get weather alerts for a US state
    
    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)
    
    if not data or "features" not in data:
        return ["Unable to fetch alerts or no alerts found."]

    if not data["features"]:
        return ["No active alerts for this state."]

    alerts = [format_alert(feature) for feature in data["features"]]
    
    return alerts

async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."
    
    return format_forecast(forecast_data)

# Specs

get_alerts_spec = types.Tool(
    name="get-alert",
    title="Get weather alert",
    description="Get weather alerts for a US state",
    inputSchema={
        "type": "object",
        "required": ["state"],
        "properties": {
            "state": {
                "type": "string",
                "description": "Two-letter US state code (e.g. CA, NY)",
            },
        },
    },
)

get_forecast_spec = types.Tool(
    name="get-forecast",
    title="Get weather forecast",
    description="Get weather forecast for a location",
    inputSchema={
        "type": "object",
        "required": ["latitude", "longitude"],
        "properties": {
            "latitude": {
                "type": "number",
                "description": "Latitude of the location",
            },
            "longitude": {
                "type": "number",
                "description": "Longitude of the location",
            }
        },
    },
)

# Handlers

async def get_alerts_handler(arguments: dict[str, Any], ctx: Any) -> list[types.ContentBlock]:
    state_raw = arguments.get("state")

    if not isinstance(state_raw, str) or len(state_raw.strip()) != 2:
        return [types.TextContent(type="text", text="Invalid state code. Provide a two-letter US state code.")]

    state = state_raw.strip().upper()

    alerts = await get_alerts(state)

    return [types.TextContent(type="text", text=alert) for alert in alerts]
    
async def get_forecast_handler(arguments: dict[str, Any], ctx: Any) -> list[types.ContentBlock]:
    raw_lat = arguments.get("latitude")
    raw_lon = arguments.get("longitude")

    if raw_lat is None or raw_lon is None:
        return [types.TextContent(type="text", text="Missing required arguments: latitude and longitude.")]

    try:
        lat = float(raw_lat)
        lon = float(raw_lon)
    except (TypeError, ValueError):
        return [types.TextContent(type="text", text="Invalid latitude/longitude. They must be numbers.")]

    forecast = await get_forecast(lat, lon)

    return [types.TextContent(type="text", text=forecast)]

def register_all() -> None:
    register_tool(get_alerts_spec, get_alerts_handler)
    register_tool(get_forecast_spec, get_forecast_handler)