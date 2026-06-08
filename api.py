"""
Railway Digital Twin API
FastAPI endpoints for platform allocation
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from supabase import create_client
from datetime import datetime
from pydantic import BaseModel

# Load environment
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY")

# Initialize
supabase = create_client(url, key)
app = FastAPI(title="Railway Digital Twin API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# MODELS
# ============================================================

class AllocationRequest(BaseModel):
    train_id: int

class AllocationResponse(BaseModel):
    status: str
    message: str
    data: dict = None

# ============================================================
# HELPER FUNCTIONS (from allocation_engine)
# ============================================================

def get_pending_trains():
    """Fetch all pending trains"""
    try:
        response = supabase.table("trains").select("*").eq("status", "PENDING").execute()
        return response.data
    except Exception as e:
        return []

def get_available_platforms():
    """Fetch all available platforms"""
    try:
        response = supabase.table("platforms").select("*").eq("status", "AVAILABLE").execute()
        return response.data
    except Exception as e:
        return []

def get_train_by_id(train_id):
    """Get specific train"""
    try:
        response = supabase.table("trains").select("*").eq("train_id", train_id).execute()
        return response.data[0] if response.data else None
    except:
        return None

def is_time_conflict(platform, arrival_time, departure_time):
    """Check time conflicts"""
    if not platform.get("occupied_until"):
        return False
    
    occupied_until = platform["occupied_until"]
    arrival_dt = datetime.strptime(arrival_time, "%H:%M:%S")
    occupied_dt = datetime.strptime(occupied_until, "%H:%M:%S")
    
    return arrival_dt < occupied_dt

def check_platform_suitability(platform, train):
    """Check if platform can fit train"""
    if platform["platform_length"] < train["train_length"]:
        return False, f"Length: {platform['platform_length']}m < {train['train_length']}m"
    
    if platform["status"] != "AVAILABLE":
        return False, f"Status: {platform['status']}"
    
    if is_time_conflict(platform, train["arrival_time"], train["departure_time"]):
        return False, f"Time conflict until {platform['occupied_until']}"
    
    return True, "Suitable"

def find_best_fit_platform(train, available_platforms):
    """Find best-fit platform"""
    suitable_platforms = []
    
    for platform in available_platforms:
        is_suitable, reason = check_platform_suitability(platform, train)
        if is_suitable:
            suitable_platforms.append(platform)
    
    if not suitable_platforms:
        return None, "No suitable platforms"
    
    best_platform = min(suitable_platforms, key=lambda p: p["platform_length"])
    return best_platform, "Best-fit selected"

def allocate_train(train, platform):
    """Allocate train to platform"""
    try:
        # Insert allocation
        allocation_data = {
            "train_id": train["train_id"],
            "platform_id": platform["platform_id"],
            "timestamp": datetime.now().isoformat()
        }
        supabase.table("allocations").insert(allocation_data).execute()
        
        # Update platform
        supabase.table("platforms").update({
            "status": "OCCUPIED",
            "occupied_until": train["departure_time"]
        }).eq("platform_id", platform["platform_id"]).execute()
        
        # Update train
        supabase.table("trains").update({
            "status": "ALLOCATED"
        }).eq("train_id", train["train_id"]).execute()
        
        return True, {
            "train_id": train["train_id"],
            "train_name": train["train_name"],
            "platform_id": platform["platform_id"],
            "platform_number": platform["platform_number"]
        }
    except Exception as e:
        return False, str(e)

# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "online",
        "message": "Railway Digital Twin API",
        "version": "1.0.0"
    }

@app.get("/trains/pending")
async def get_pending():
    """Get all pending trains"""
    trains = get_pending_trains()
    return {
        "status": "success",
        "count": len(trains),
        "data": trains
    }

@app.get("/platforms/available")
async def get_platforms():
    """Get all available platforms"""
    platforms = get_available_platforms()
    return {
        "status": "success",
        "count": len(platforms),
        "data": platforms
    }

@app.post("/allocate/single")
async def allocate_single(request: AllocationRequest):
    """Allocate single train"""
    
    # Get train
    train = get_train_by_id(request.train_id)
    if not train:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Train not found"}
        )
    
    # Get available platforms
    available_platforms = get_available_platforms()
    if not available_platforms:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "No available platforms"}
        )
    
    # Find best platform
    platform, reason = find_best_fit_platform(train, available_platforms)
    if not platform:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": reason}
        )
    
    # Allocate
    success, result = allocate_train(train, platform)
    if success:
        return {
            "status": "success",
            "message": "Train allocated successfully",
            "data": result
        }
    else:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": result}
        )

@app.post("/allocate/all")
async def allocate_all():
    """Allocate all pending trains"""
    
    pending_trains = get_pending_trains()
    if not pending_trains:
        return {"status": "success", "message": "No pending trains"}
    
    available_platforms = get_available_platforms()
    if not available_platforms:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "No available platforms"}
        )
    
    allocations = []
    failed = []
    
    for train in pending_trains:
        platform, reason = find_best_fit_platform(train, available_platforms)
        
        if platform:
            success, result = allocate_train(train, platform)
            if success:
                allocations.append(result)
                available_platforms = [p for p in available_platforms 
                                      if p["platform_id"] != platform["platform_id"]]
            else:
                failed.append({"train_id": train["train_id"], "error": result})
        else:
            failed.append({"train_id": train["train_id"], "error": reason})
    
    return {
        "status": "success",
        "message": f"Allocated {len(allocations)} trains",
        "allocated": allocations,
        "failed": failed,
        "total": len(pending_trains)
    }

@app.get("/allocations")
async def get_allocations():
    """Get all allocations"""
    try:
        response = supabase.table("allocations").select("*").execute()
        return {
            "status": "success",
            "count": len(response.data),
            "data": response.data
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.get("/status")
async def get_status():
    """Get system status"""
    try:
        pending_trains = supabase.table("trains").select("*").eq("status", "PENDING").execute()
        allocated_trains = supabase.table("trains").select("*").eq("status", "ALLOCATED").execute()
        available_platforms = supabase.table("platforms").select("*").eq("status", "AVAILABLE").execute()
        occupied_platforms = supabase.table("platforms").select("*").eq("status", "OCCUPIED").execute()
        
        return {
            "status": "success",
            "summary": {
                "pending_trains": len(pending_trains.data),
                "allocated_trains": len(allocated_trains.data),
                "available_platforms": len(available_platforms.data),
                "occupied_platforms": len(occupied_platforms.data)
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)