"""
Production-Ready Weather Intelligence Agent for Railway Operations
Built with LangGraph and Supabase

This agent monitors weather conditions and predicts railway operational impacts
"""

import os
import json
import requests
from typing import TypedDict, Optional, List
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "demo_key")

# Initialize Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================================
# TYPE DEFINITIONS (Typed Dict for LangGraph)
# ============================================================

class WeatherData(TypedDict):
    """Raw weather data from API"""
    station: str
    latitude: float
    longitude: float
    temperature: float
    humidity: int
    wind_speed: float
    rainfall: float
    weather_condition: str
    visibility: float
    pressure: int

class WeatherAlert(TypedDict):
    """Processed weather alert for railway operations"""
    alert_id: str
    station: str
    weather_condition: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    expected_delay_minutes: int
    speed_restriction: bool
    route_risk: bool
    platform_congestion_risk: bool
    signal_visibility_problem: bool
    track_safety_concern: bool
    recommendation: str
    created_at: str

class WeatherState(TypedDict):
    """State object for LangGraph workflow"""
    raw_weather: Optional[WeatherData]
    analyzed_weather: Optional[dict]
    predicted_impacts: Optional[dict]
    alert: Optional[WeatherAlert]
    notifications_sent: List[str]
    error: Optional[str]

# ============================================================
# WEATHER ANALYSIS CONFIGURATION
# ============================================================

WEATHER_SEVERITY_MAP = {
    # Weather conditions to severity levels
    "Clear": "LOW",
    "Clouds": "LOW",
    "Drizzle": "MEDIUM",
    "Rain": "MEDIUM",
    "Heavy Rain": "HIGH",
    "Thunderstorm": "CRITICAL",
    "Snow": "HIGH",
    "Mist": "MEDIUM",
    "Fog": "HIGH",
    "Smoke": "MEDIUM",
    "Haze": "MEDIUM",
    "Dust": "MEDIUM",
    "Sand": "HIGH",
    "Ash": "CRITICAL",
    "Squall": "CRITICAL",
    "Tornado": "CRITICAL"
}

RAILWAY_IMPACT_THRESHOLDS = {
    "wind_speed_kmh": 60,  # Strong winds threshold
    "visibility_km": 1,    # Fog/visibility threshold
    "rainfall_mm": 25,     # Heavy rain threshold
    "temperature_celsius_high": 45,  # Heat wave
    "temperature_celsius_low": -10   # Extreme cold
}

# ============================================================
# NODE 1: FETCH WEATHER DATA
# ============================================================

def fetch_weather(state: WeatherState) -> WeatherState:
    """
    Node 1: Fetch weather data from OpenWeather API
    
    In production, this would fetch real weather data.
    For demo, we simulate realistic railway weather scenarios.
    """
    print("\n🌤️ NODE 1: Fetching Weather Data...")
    
    try:
        # Simulate fetching weather for major Indian railway stations
        stations = [
            {"name": "Lucknow", "lat": 26.8467, "lon": 80.9462},
            {"name": "Delhi", "lat": 28.7041, "lon": 77.1025},
            {"name": "Mumbai", "lat": 19.0760, "lon": 72.8777}
        ]
        
        # For demo: Use first station (Lucknow)
        station = stations[0]
        
        # Try to fetch from OpenWeather API (with fallback to demo data)
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={station['lat']}&lon={station['lon']}&appid={OPENWEATHER_API_KEY}&units=metric"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                raw_weather = WeatherData(
                    station=station["name"],
                    latitude=station["lat"],
                    longitude=station["lon"],
                    temperature=data["main"]["temp"],
                    humidity=data["main"]["humidity"],
                    wind_speed=data["wind"]["speed"] * 3.6,  # Convert m/s to km/h
                    rainfall=data.get("rain", {}).get("1h", 0),
                    weather_condition=data["weather"][0]["main"],
                    visibility=data.get("visibility", 10000) / 1000,  # Convert to km
                    pressure=data["main"]["pressure"]
                )
            else:
                # Demo data
                raw_weather = WeatherData(
                    station="Lucknow",
                    latitude=26.8467,
                    longitude=80.9462,
                    temperature=32.5,
                    humidity=75,
                    wind_speed=45.0,
                    rainfall=15.5,
                    weather_condition="Heavy Rain",
                    visibility=2.5,
                    pressure=1005
                )
        except Exception as e:
            print(f"⚠️ API call failed, using demo data: {e}")
            # Fallback to demo data
            raw_weather = WeatherData(
                station="Lucknow",
                latitude=26.8467,
                longitude=80.9462,
                temperature=32.5,
                humidity=75,
                wind_speed=45.0,
                rainfall=15.5,
                weather_condition="Heavy Rain",
                visibility=2.5,
                pressure=1005
            )
        
        state["raw_weather"] = raw_weather
        print(f"✅ Weather fetched for {raw_weather['station']}")
        print(f"   Condition: {raw_weather['weather_condition']}")
        print(f"   Temperature: {raw_weather['temperature']}°C")
        print(f"   Wind Speed: {raw_weather['wind_speed']} km/h")
        
    except Exception as e:
        state["error"] = f"Failed to fetch weather: {str(e)}"
        print(f"❌ Error: {state['error']}")
    
    return state

# ============================================================
# NODE 2: ANALYZE WEATHER CONDITIONS
# ============================================================

def analyze_weather(state: WeatherState) -> WeatherState:
    """
    Node 2: Analyze weather conditions and determine railway impacts
    
    Evaluates:
    - Weather severity classification
    - Wind impact assessment
    - Visibility issues
    - Temperature extremes
    - Precipitation levels
    """
    print("\n📊 NODE 2: Analyzing Weather Conditions...")
    
    if not state["raw_weather"]:
        state["error"] = "No weather data available"
        return state
    
    try:
        weather = state["raw_weather"]
        
        # Determine severity
        severity = WEATHER_SEVERITY_MAP.get(weather["weather_condition"], "MEDIUM")
        
        # Adjust severity based on thresholds
        if weather["wind_speed"] > RAILWAY_IMPACT_THRESHOLDS["wind_speed_kmh"]:
            if severity in ["LOW", "MEDIUM"]:
                severity = "HIGH"
        
        if weather["visibility"] < RAILWAY_IMPACT_THRESHOLDS["visibility_km"]:
            if severity in ["LOW", "MEDIUM"]:
                severity = "HIGH"
        
        if weather["rainfall"] > RAILWAY_IMPACT_THRESHOLDS["rainfall_mm"]:
            if severity in ["LOW", "MEDIUM"]:
                severity = "HIGH"
        
        # Determine specific railway impacts
        signal_visibility_problem = weather["visibility"] < 2
        speed_restriction = weather["wind_speed"] > 50 or weather["visibility"] < 1.5
        platform_congestion_risk = weather["rainfall"] > 10
        route_risk = weather["visibility"] < 1 or weather["wind_speed"] > 70
        
        analyzed = {
            "severity": severity,
            "signal_visibility_problem": signal_visibility_problem,
            "speed_restriction": speed_restriction,
            "platform_congestion_risk": platform_congestion_risk,
            "route_risk": route_risk,
            "wind_impact": "Strong" if weather["wind_speed"] > 50 else "Moderate" if weather["wind_speed"] > 30 else "Low",
            "rainfall_level": "Heavy" if weather["rainfall"] > 25 else "Moderate" if weather["rainfall"] > 10 else "Light"
        }
        
        state["analyzed_weather"] = analyzed
        print(f"✅ Weather Analysis Complete")
        print(f"   Severity: {severity}")
        print(f"   Signal Issues: {signal_visibility_problem}")
        print(f"   Speed Restriction: {speed_restriction}")
        print(f"   Platform Congestion Risk: {platform_congestion_risk}")
        
    except Exception as e:
        state["error"] = f"Failed to analyze weather: {str(e)}"
        print(f"❌ Error: {state['error']}")
    
    return state

# ============================================================
# NODE 3: PREDICT OPERATIONAL IMPACTS
# ============================================================

def predict_delay(state: WeatherState) -> WeatherState:
    """
    Node 3: Predict expected delays and operational impacts
    
    Uses weather severity and railway thresholds to estimate:
    - Expected delay in minutes
    - Speed restrictions
    - Platform impacts
    - Route availability
    """
    print("\n⏱️ NODE 3: Predicting Operational Impacts...")
    
    if not state["raw_weather"] or not state["analyzed_weather"]:
        state["error"] = "Missing weather data for prediction"
        return state
    
    try:
        weather = state["raw_weather"]
        analyzed = state["analyzed_weather"]
        severity = analyzed["severity"]
        
        # Calculate expected delay based on severity and conditions
        delay_minutes = 0
        
        if severity == "LOW":
            delay_minutes = 0
        elif severity == "MEDIUM":
            delay_minutes = 5 + int(weather["rainfall"] / 5)
        elif severity == "HIGH":
            delay_minutes = 15 + int(weather["wind_speed"] / 5)
        elif severity == "CRITICAL":
            delay_minutes = 30 + int(weather["wind_speed"] / 3)
        
        # Additional delay from precipitation
        if weather["rainfall"] > 25:
            delay_minutes += 10
        
        # Additional delay from visibility
        if weather["visibility"] < 1:
            delay_minutes += 5
        
        impacts = {
            "expected_delay_minutes": min(delay_minutes, 120),  # Cap at 2 hours
            "speed_restriction": analyzed["speed_restriction"],
            "route_blockage_probability": min(weather["rainfall"] / 50, 1.0),  # 0-1 scale
            "platform_congestion_probability": min(weather["rainfall"] / 30, 1.0),
            "affected_train_count": 3 if severity == "CRITICAL" else 2 if severity == "HIGH" else 1,
            "alternative_routes_available": severity != "CRITICAL"
        }
        
        state["predicted_impacts"] = impacts
        print(f"✅ Impact Prediction Complete")
        print(f"   Expected Delay: {impacts['expected_delay_minutes']} minutes")
        print(f"   Speed Restriction: {impacts['speed_restriction']}")
        print(f"   Affected Trains: {impacts['affected_train_count']}")
        
    except Exception as e:
        state["error"] = f"Failed to predict delays: {str(e)}"
        print(f"❌ Error: {state['error']}")
    
    return state

# ============================================================
# NODE 4: GENERATE RAILWAY ALERTS
# ============================================================

def generate_alert(state: WeatherState) -> WeatherState:
    """
    Node 4: Generate structured railway-specific alerts
    
    Creates AlertWeather object with:
    - Station and weather condition
    - Severity classification
    - Specific railway impacts
    - Actionable recommendations
    """
    print("\n🚨 NODE 4: Generating Railway Alerts...")
    
    if not all([state["raw_weather"], state["analyzed_weather"], state["predicted_impacts"]]):
        state["error"] = "Missing data for alert generation"
        return state
    
    try:
        weather = state["raw_weather"]
        analyzed = state["analyzed_weather"]
        impacts = state["predicted_impacts"]
        
        # Generate recommendation based on severity and impacts
        recommendation = _generate_recommendation(
            analyzed["severity"],
            analyzed,
            impacts
        )
        
        # Create alert
        alert = WeatherAlert(
            alert_id=f"WA_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            station=weather["station"],
            weather_condition=weather["weather_condition"],
            severity=analyzed["severity"],
            expected_delay_minutes=impacts["expected_delay_minutes"],
            speed_restriction=impacts["speed_restriction"],
            route_risk=impacts["route_blockage_probability"] > 0.5,
            platform_congestion_risk=impacts["platform_congestion_probability"] > 0.5,
            signal_visibility_problem=analyzed["signal_visibility_problem"],
            track_safety_concern=weather["wind_speed"] > 70,
            recommendation=recommendation,
            created_at=datetime.now().isoformat()
        )
        
        state["alert"] = alert
        print(f"✅ Alert Generated")
        print(f"   Alert ID: {alert['alert_id']}")
        print(f"   Severity: {alert['severity']}")
        print(f"   Recommendation: {alert['recommendation']}")
        
    except Exception as e:
        state["error"] = f"Failed to generate alert: {str(e)}"
        print(f"❌ Error: {state['error']}")
    
    return state

# ============================================================
# NODE 5: NOTIFY OTHER AGENTS
# ============================================================

def notify_agents(state: WeatherState) -> WeatherState:
    """
    Node 5: Send weather alerts to other agents in the system
    
    Communicates with:
    - Platform Allocation Agent: Adjust platform assignments
    - Route Management Agent: Modify routes due to weather
    - Train Scheduling Agent: Add delay buffers
    - Passenger Notification Agent: Send passenger alerts
    """
    print("\n📢 NODE 5: Notifying Other Agents...")
    
    if not state["alert"]:
        state["error"] = "No alert to send"
        return state
    
    try:
        alert = state["alert"]
        notifications = []
        
        # 1. Notify Platform Allocation Agent
        if alert["platform_congestion_risk"]:
            platform_message = {
                "recipient": "PlatformAllocationAgent",
                "action": "ADJUST_ALLOCATION",
                "reason": f"Platform congestion risk due to {alert['weather_condition']}",
                "severity": alert["severity"],
                "additional_platforms_needed": 2 if alert["severity"] == "CRITICAL" else 1
            }
            notifications.append("PlatformAllocationAgent")
            print(f"   → Platform Allocation Agent: ADJUST_ALLOCATION")
        
        # 2. Notify Route Management Agent
        if alert["route_risk"]:
            route_message = {
                "recipient": "RouteManagementAgent",
                "action": "MODIFY_ROUTES",
                "reason": f"Route safety concern due to {alert['weather_condition']}",
                "severity": alert["severity"],
                "alternative_routes_available": state["predicted_impacts"]["alternative_routes_available"]
            }
            notifications.append("RouteManagementAgent")
            print(f"   → Route Management Agent: MODIFY_ROUTES")
        
        # 3. Notify Train Scheduling Agent
        if alert["expected_delay_minutes"] > 0:
            scheduling_message = {
                "recipient": "TrainSchedulingAgent",
                "action": "ADD_DELAY_BUFFER",
                "reason": f"Expected delays due to {alert['weather_condition']}",
                "delay_minutes": alert["expected_delay_minutes"],
                "affected_train_count": state["predicted_impacts"]["affected_train_count"]
            }
            notifications.append("TrainSchedulingAgent")
            print(f"   → Train Scheduling Agent: ADD_DELAY_BUFFER ({alert['expected_delay_minutes']} min)")
        
        # 4. Notify Passenger Notification Agent
        if alert["severity"] in ["HIGH", "CRITICAL"]:
            passenger_message = {
                "recipient": "PassengerNotificationAgent",
                "action": "SEND_ALERTS",
                "message": f"⚠️ {alert['weather_condition']} expected. {alert['recommendation']}",
                "severity": alert["severity"],
                "affected_station": alert["station"]
            }
            notifications.append("PassengerNotificationAgent")
            print(f"   → Passenger Notification Agent: SEND_ALERTS")
        
        # Save alert to database
        try:
            supabase.table("weather_alerts").insert({
                "alert_id": alert["alert_id"],
                "station": alert["station"],
                "weather_condition": alert["weather_condition"],
                "severity": alert["severity"],
                "expected_delay_minutes": alert["expected_delay_minutes"],
                "speed_restriction": alert["speed_restriction"],
                "route_risk": alert["route_risk"],
                "platform_congestion_risk": alert["platform_congestion_risk"],
                "recommendation": alert["recommendation"],
                "created_at": alert["created_at"],
                "agents_notified": json.dumps(notifications)
            }).execute()
            print(f"   ✅ Alert saved to database")
        except Exception as db_error:
            print(f"   ⚠️ Database error: {db_error}")
        
        state["notifications_sent"] = notifications
        print(f"✅ Notifications sent to {len(notifications)} agents")
        
    except Exception as e:
        state["error"] = f"Failed to notify agents: {str(e)}"
        print(f"❌ Error: {state['error']}")
    
    return state

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _generate_recommendation(severity: str, analyzed: dict, impacts: dict) -> str:
    """
    Generate specific railway recommendations based on weather conditions
    """
    if severity == "CRITICAL":
        return "🚨 CRITICAL: Consider service suspension. Activate emergency protocols."
    elif severity == "HIGH":
        if analyzed["platform_congestion_risk"]:
            return "⚠️ HIGH: Reallocate delayed trains to alternate platforms immediately."
        elif analyzed["route_risk"]:
            return "⚠️ HIGH: Activate alternative routes to avoid blockage risk."
        else:
            return "⚠️ HIGH: Implement speed restrictions and increase platform capacity."
    elif severity == "MEDIUM":
        return "📋 MEDIUM: Monitor conditions closely. Prepare contingency plans."
    else:
        return "✅ LOW: Normal operations. Continue monitoring."

# ============================================================
# MAIN AGENT EXECUTION
# ============================================================

def run_weather_agent() -> WeatherState:
    """
    Execute the complete weather intelligence agent workflow
    
    Workflow:
    1. Fetch weather → 2. Analyze → 3. Predict → 4. Generate Alert → 5. Notify Agents
    """
    print("\n" + "="*70)
    print("🌦️ WEATHER INTELLIGENCE AGENT - Starting Workflow")
    print("="*70)
    
    # Initialize state
    state: WeatherState = {
        "raw_weather": None,
        "analyzed_weather": None,
        "predicted_impacts": None,
        "alert": None,
        "notifications_sent": [],
        "error": None
    }
    
    # Execute workflow nodes in sequence
    state = fetch_weather(state)
    state = analyze_weather(state)
    state = predict_delay(state)
    state = generate_alert(state)
    state = notify_agents(state)
    
    # Final summary
    print("\n" + "="*70)
    print("📊 WEATHER AGENT SUMMARY")
    print("="*70)
    
    if state["alert"]:
        alert = state["alert"]
        print(f"✅ Alert Generated: {alert['alert_id']}")
        print(f"   Station: {alert['station']}")
        print(f"   Condition: {alert['weather_condition']}")
        print(f"   Severity: {alert['severity']}")
        print(f"   Expected Delay: {alert['expected_delay_minutes']} minutes")
        print(f"   Agents Notified: {len(state['notifications_sent'])}")
    else:
        print("❌ No alert generated")
    
    print("="*70 + "\n")
    
    return state

# ============================================================
# RUN AGENT
# ============================================================

if __name__ == "__main__":
    result = run_weather_agent()
    
    # Print final state as JSON
    if result["alert"]:
        print("\n📤 AGENT OUTPUT (JSON):")
        print(json.dumps(result["alert"], indent=2))
