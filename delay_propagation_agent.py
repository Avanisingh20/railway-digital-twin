"""
Agent 5: Delay Propagation Agent
Railway Digital Twin - FAR AWAY 2026 Hackathon

This agent:
1. Detects train delays
2. Tracks cascading effects (which trains are affected)
3. Calculates impact on platforms, signals, crew
4. Updates database with delay propagation
5. Provides mitigation strategies
"""

from dotenv import load_dotenv
import os
from supabase import create_client
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

# Load environment
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY")

supabase = create_client(url, key)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_all_trains() -> List[Dict]:
    """Fetch all trains"""
    try:
        response = supabase.table("trains").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"❌ Error fetching trains: {e}")
        return []

def get_allocations() -> List[Dict]:
    """Fetch all allocations"""
    try:
        response = supabase.table("allocations").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"❌ Error fetching allocations: {e}")
        return []

def simulate_delay(train: Dict) -> Tuple[int, str]:
    """
    Simulate delay for a train
    In real system, this would come from sensors/tracking
    
    Rules:
    - EXPRESS trains: 5-10 min delays (rare)
    - PREMIUM trains: 8-15 min delays
    - NORMAL trains: 10-30 min delays
    - FREIGHT: 15-45 min delays
    """
    import random
    
    priority = str(train.get("priority", "NORMAL")).upper()
    delay_causes = {
        "EXPRESS": (5, 10, "Signal delay"),
        "PREMIUM": (8, 15, "Track maintenance"),
        "VERY_HIGH": (8, 15, "Coupling issue"),
        "HIGH": (10, 25, "Platform congestion"),
        "1": (5, 10, "Weather"),
        "2": (10, 20, "Crew delay"),
        "3": (15, 40, "Mechanical issue"),
        "NORMAL": (10, 30, "Station delay"),
        "FREIGHT": (15, 45, "Loading delay")
    }
    
    min_delay, max_delay, cause = delay_causes.get(priority, (10, 30, "Unknown"))
    delay_minutes = random.randint(min_delay, max_delay)
    
    return delay_minutes, cause

def detect_affected_trains(delayed_train: Dict, delay_minutes: int, all_trains: List[Dict], allocations: List[Dict]) -> List[Dict]:
    """
    Detect which trains are affected by a delay
    
    A train is affected if:
    1. It arrives shortly after the delayed train departs from same platform
    2. It requires crew that was on the delayed train
    3. It's a connecting train from same origin
    """
    affected = []
    
    # Get platform used by delayed train
    delayed_allocation = next(
        (a for a in allocations if a.get("train_id") == delayed_train["train_id"]),
        None
    )
    
    if not delayed_allocation:
        return affected
    
    delayed_platform_id = delayed_allocation.get("platform_id")
    
    # Original departure time
    original_departure = datetime.strptime(delayed_train["departure_time"], "%H:%M:%S")
    # New departure time (with delay)
    new_departure = original_departure + timedelta(minutes=delay_minutes)
    
    # Find trains affected
    for other_train in all_trains:
        if other_train["train_id"] == delayed_train["train_id"]:
            continue
        
        other_arrival = datetime.strptime(other_train["arrival_time"], "%H:%M:%S")
        
        # Check 1: Uses same platform within buffer time
        other_allocation = next(
            (a for a in allocations if a.get("train_id") == other_train["train_id"]),
            None
        )
        
        if other_allocation and other_allocation.get("platform_id") == delayed_platform_id:
            # Platform not freed up in time
            if other_arrival <= new_departure:
                affected.append({
                    "train_id": other_train["train_id"],
                    "train_name": other_train["train_name"],
                    "impact_type": "PLATFORM_BLOCKED",
                    "impact_minutes": (new_departure - other_arrival).total_seconds() // 60,
                    "reason": f"Platform {delayed_platform_id} blocked until {new_departure.strftime('%H:%M:%S')}"
                })
        
        # Check 2: Crew connection (different train arriving after delayed train departs)
        time_between = (other_arrival - new_departure).total_seconds() // 60
        if 0 < time_between < 30:  # Less than 30 mins between trains
            affected.append({
                "train_id": other_train["train_id"],
                "train_name": other_train["train_name"],
                "impact_type": "CREW_CONNECTION",
                "impact_minutes": 30 - time_between,
                "reason": "Tight crew connection window (only 30 min buffer)"
            })
    
    # Remove duplicates
    seen = set()
    unique_affected = []
    for item in affected:
        key = (item["train_id"], item["impact_type"])
        if key not in seen:
            seen.add(key)
            unique_affected.append(item)
    
    return unique_affected

def save_delay_to_db(train: Dict, delay_minutes: int, cause: str):
    """Save delay record to database"""
    try:
        original_arrival = datetime.strptime(train["arrival_time"], "%H:%M:%S")
        actual_arrival = original_arrival + timedelta(minutes=delay_minutes)
        
        delay_record = {
            "train_id": train["train_id"],
            "original_arrival_time": train["arrival_time"],
            "actual_arrival_time": actual_arrival.strftime("%H:%M:%S"),
            "delay_minutes": delay_minutes,
            "delay_cause": cause,
            "detected_at": datetime.now().isoformat(),
            "status": "ACTIVE"
        }
        
        supabase.table("delays").insert(delay_record).execute()
        return True
    except Exception as e:
        print(f"❌ Error saving delay: {e}")
        return False

def get_mitigation_strategy(delayed_train: Dict, affected_trains: List[Dict]) -> str:
    """
    Suggest mitigation strategy
    """
    if not affected_trains:
        return "No affected trains - delay is isolated"
    
    platform_impacts = len([t for t in affected_trains if t["impact_type"] == "PLATFORM_BLOCKED"])
    crew_impacts = len([t for t in affected_trains if t["impact_type"] == "CREW_CONNECTION"])
    
    strategies = []
    
    if platform_impacts > 0:
        strategies.append(f"🔄 Reroute {platform_impacts} trains to different platforms")
    
    if crew_impacts > 0:
        strategies.append(f"👥 Arrange backup crew for {crew_impacts} trains")
    
    if len(affected_trains) > 3:
        strategies.append("⚠️ ALERT: Cascade alert - high impact on network")
    
    return " | ".join(strategies) if strategies else "Monitor situation"

# ============================================================
# MAIN DELAY PROPAGATION ENGINE
# ============================================================

def run_delay_propagation():
    """
    Main engine: Detect and propagate all delays
    """
    print("\n" + "="*80)
    print("🚂 DELAY PROPAGATION AGENT - Starting Analysis")
    print("="*80)
    
    # Fetch data
    all_trains = get_all_trains()
    allocations = get_allocations()
    
    print(f"\n📊 Total Trains in System: {len(all_trains)}")
    print(f"📍 Current Allocations: {len(allocations)}")
    
    if not all_trains:
        print("⚠️ No trains in system")
        return
    
    print(f"\n🔍 Simulating delays for EXPRESS and PREMIUM trains...\n")
    
    # Simulate delays for some high-priority trains
    delayed_trains = []
    import random
    high_priority_trains = [
        t for t in all_trains 
        if str(t.get("priority", "")).upper() in ["EXPRESS", "PREMIUM", "VERY_HIGH", "1"]
    ]
    
    # Randomly select 2-3 trains to have delays
    trains_with_delays = random.sample(
        high_priority_trains,
        min(2, len(high_priority_trains))
    )
    
    for train in trains_with_delays:
        delay_minutes, cause = simulate_delay(train)
        affected_trains = detect_affected_trains(train, delay_minutes, all_trains, allocations)
        
        print(f"⚠️ DELAY DETECTED")
        print(f"  Train: {train['train_name']} ({train['train_number']})")
        print(f"  Original Arrival: {train['arrival_time']}")
        print(f"  Delay: {delay_minutes} minutes")
        print(f"  Cause: {cause}")
        print(f"  Priority: {train.get('priority', 'NORMAL')}")
        
        # Save to database
        save_delay_to_db(train, delay_minutes, cause)
        
        # Track cascading effects
        print(f"\n  🔗 Cascading Effects: {len(affected_trains)} trains affected")
        
        if affected_trains:
            for idx, affected in enumerate(affected_trains, 1):
                print(f"     {idx}. {affected['train_name']}")
                print(f"        Impact Type: {affected['impact_type']}")
                print(f"        Impact: {affected['impact_minutes']:.0f} minutes")
                print(f"        Reason: {affected['reason']}")
        else:
            print(f"     ✅ No cascading impacts")
        
        # Mitigation strategy
        strategy = get_mitigation_strategy(train, affected_trains)
        print(f"\n  💡 Mitigation: {strategy}")
        
        delayed_trains.append({
            "train": train,
            "delay_minutes": delay_minutes,
            "affected_count": len(affected_trains),
            "strategy": strategy
        })
        
        print(f"\n{'-'*80}\n")
    
    # Summary
    print("="*80)
    print(f"📊 DELAY PROPAGATION SUMMARY")
    print("="*80)
    print(f"Trains with Delays: {len(delayed_trains)}")
    total_affected = sum(d["affected_count"] for d in delayed_trains)
    print(f"Total Trains Affected by Cascade: {total_affected}")
    
    if delayed_trains:
        avg_delay = sum(d["delay_minutes"] for d in delayed_trains) / len(delayed_trains)
        print(f"Average Delay: {avg_delay:.0f} minutes")
        
        max_cascade = max(d["affected_count"] for d in delayed_trains)
        print(f"Largest Cascade: {max_cascade} trains")
    
    print("="*80 + "\n")

# ============================================================
# RUN THE AGENT
# ============================================================

if __name__ == "__main__":
    run_delay_propagation()