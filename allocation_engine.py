from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)

print("\n🚂 STARTING ALLOCATION ENGINE...\n")

# STEP 1: FETCH DATA
trains = supabase.table("trains").select("*").eq("status", "PENDING").execute().data
platforms = supabase.table("platforms").select("*").execute().data

print(f"📥 Pending Trains: {len(trains)}")
print(f"🚉 Total Platforms: {len(platforms)}\n")

# STEP 2: TRACK USED PLATFORMS (in current run)
used_platform_ids = set()

# STEP 3: SORT TRAINS BY PRIORITY (1 = highest priority)
trains = sorted(trains, key=lambda x: int(x["priority"]))

# STEP 4: ALLOCATION LOOP
for train in trains:

    print(f"➡ Processing Train: {train['train_number']} (Priority {train['priority']})")

    # FILTER VALID PLATFORMS
    valid_platforms = [
        p for p in platforms
        if p["status"] == "AVAILABLE"
        and p["platform_length"] >= train["train_length"]
        and p["platform_id"] not in used_platform_ids
    ]

    # NO PLATFORM FOUND
    if not valid_platforms:
        print("❌ No suitable platform found\n")
        continue

    # PICK BEST FIT (smallest suitable platform)
    best_platform = min(valid_platforms, key=lambda x: x["platform_length"])

    # MARK PLATFORM AS USED (prevent duplicate in same run)
    used_platform_ids.add(best_platform["platform_id"])

    print(f"✅ Assigned Platform {best_platform['platform_number']}")

    # STEP 5: INSERT INTO ALLOCATIONS
    supabase.table("allocations").insert({
        "train_id": train["train_id"],
        "platform_id": best_platform["platform_id"]
    }).execute()

    # STEP 6: UPDATE TRAIN STATUS
    supabase.table("trains").update({
        "status": "ALLOCATED"
    }).eq("train_id", train["train_id"]).execute()

    # STEP 7: UPDATE PLATFORM STATUS
    supabase.table("platforms").update({
        "status": "OCCUPIED"
    }).eq("platform_id", best_platform["platform_id"]).execute()

    print("📦 Saved + Database Updated\n")

print("🚂 ALLOCATION COMPLETE")