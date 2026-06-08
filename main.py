from dotenv import load_dotenv
import os
from supabase import create_client
import socket
import urllib.request

# Load .env
load_dotenv()

# Read environment variables
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# STEP 1: Basic validation
print("=" * 50)
print("STEP 1: Environment Variables")
print("=" * 50)
if not url or not key:
    raise ValueError("❌ Missing SUPABASE_URL or SUPABASE_KEY in .env")

print(f"✅ URL: {url}")
print(f"✅ Key: {key[:20]}...")

# STEP 2: Test internet connectivity
print("\n" + "=" * 50)
print("STEP 2: Internet Connectivity Check")
print("=" * 50)
try:
    # Try to reach Google's DNS (reliable connectivity test)
    socket.create_connection(("8.8.8.8", 53), timeout=3)
    print("✅ Internet connection: OK")
except (socket.timeout, socket.error) as e:
    print(f"❌ No internet connection detected: {e}")
    print("   → Check your WiFi/Ethernet connection")
    exit(1)

# STEP 3: DNS Check
print("\n" + "=" * 50)
print("STEP 3: DNS Resolution")
print("=" * 50)
try:
    host = url.replace("https://", "").replace("http://", "")
    print(f"Resolving: {host}")
    ip = socket.gethostbyname(host)
    print(f"✅ DNS resolved to: {ip}")
except socket.gaierror as e:
    print(f"❌ DNS Resolution failed: {e}")
    print("   Possible causes:")
    print("   → Supabase domain doesn't exist")
    print("   → Typo in SUPABASE_URL")
    print("   → DNS server not responding")
    print("   → Network firewall blocking DNS")
    exit(1)

# STEP 4: Test HTTP connectivity to Supabase
print("\n" + "=" * 50)
print("STEP 4: HTTP Connectivity to Supabase")
print("=" * 50)
try:
    response = urllib.request.urlopen(url, timeout=5)
    print(f"✅ HTTP Connection successful (Status: {response.status})")
except urllib.error.URLError as e:
    print(f"⚠️  HTTP connection failed: {e}")
    print("   (This is OK if Supabase returns auth error - means server is reachable)")

# STEP 5: Create Supabase client
print("\n" + "=" * 50)
print("STEP 5: Supabase Client Initialization")
print("=" * 50)
try:
    supabase = create_client(url, key)
    print("✅ Supabase client created successfully!")
except Exception as e:
    print(f"❌ Client creation failed: {e}")
    exit(1)

# STEP 6: Database query test
print("\n" + "=" * 50)
print("STEP 6: Database Query Test")
print("=" * 50)
try:
    response = supabase.table("platforms").select("*").execute()
    print(f"✅ Query successful!")
    print(f"📦 Returned {len(response.data)} rows:")
    print(response.data[:5])  # Show first 5 rows
except Exception as e:
    print(f"❌ Query failed: {e}")
    print("\n⚠️  If this is an auth error, your network is working!")
    print("    Check your Supabase key and table name instead.")
    exit(1)

print("\n" + "=" * 50)
print("✅ ALL CHECKS PASSED!")
print("=" * 50)