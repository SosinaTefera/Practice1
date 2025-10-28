import json

import requests

base_url = "http://127.0.0.1:8000"

# Test endpoints with proper parameters
endpoints = [
    {"url": "/api/v1/clients", "method": "GET", "name": "Get Clients", "params": {}},
    {
        "url": "/api/v1/exercises",
        "method": "GET",
        "name": "Get Exercises",
        "params": {},
    },
    {"url": "/api/v1/trainers", "method": "GET", "name": "Get Trainers", "params": {}},
    {
        "url": "/api/v1/training-plans",
        "method": "GET",
        "name": "Get Training Plans",
        "params": {"trainer_id": 1},
    },
    {
        "url": "/api/v1/training-sessions",
        "method": "GET",
        "name": "Get Training Sessions",
        "params": {"client_id": 1},
    },
    {
        "url": "/api/v1/standalone-sessions",
        "method": "GET",
        "name": "Get Standalone Sessions",
        "params": {"client_id": 1},
    },
]

print("🔍 Testing All Endpoints...")
print("=" * 50)

passed = 0
failed = 0

for endpoint in endpoints:
    try:
        print(f"Testing: {endpoint['name']} ({endpoint['method']} {endpoint['url']})")

        if endpoint["method"] == "GET":
            response = requests.get(
                base_url + endpoint["url"], params=endpoint["params"]
            )

        status = response.status_code
        if status < 400:  # 200, 201, 204 are success, 400+ are client/server errors
            print(f"✅ {endpoint['name']}: {status} - PASSED")
            passed += 1
        else:
            print(f"❌ {endpoint['name']}: {status} - FAILED")
            print(f"   Response: {response.text[:100]}...")
            failed += 1

    except Exception as e:
        print(f"💥 {endpoint['name']}: ERROR - {e}")
        failed += 1

    print("-" * 30)

print("=" * 50)
print(f"📊 RESULTS: {passed} PASSED, {failed} FAILED")
print(f"🎯 SUCCESS RATE: {(passed/(passed+failed)*100):.1f}%")

if failed == 0:
    print("🎉 All endpoints are working!")
else:
    print("⚠️  Some endpoints have issues. Check the errors above.")
