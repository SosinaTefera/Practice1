#!/usr/bin/env python3
"""
Debug script to test imperial input and see what's failing.
"""

import json
from datetime import date, timedelta

import requests

# API base URL
BASE_URL = "http://127.0.0.1:8000/api/v1"


def debug_imperial():
    """Debug imperial input issue"""

    print("🔍 Debugging Imperial Input")
    print("=" * 40)

    # Test imperial input step by step
    imperial_data = {
        "client_id": 1,
        "fecha_registro": str(
            date.today() + timedelta(days=2004)
        ),  # New unique future date
        "peso": 165,  # 165 lbs
        "altura": 69,  # 69 inches
        "unidad": "imperial",
        "notas": "Debug imperial input",
    }

    print(f"📤 Sending data: {json.dumps(imperial_data, indent=2)}")

    try:
        response = requests.post(f"{BASE_URL}/progress/", json=imperial_data)
        print(f"📥 Response status: {response.status_code}")
        print(f"📥 Response headers: {dict(response.headers)}")

        if response.status_code == 201:
            print("✅ Success!")
            result = response.json()
            print(f"📊 Result: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"📄 Response body: {response.text}")

            # Try to parse error details
            try:
                error_detail = response.json()
                print(f"🔍 Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print("🔍 Could not parse error response as JSON")

    except Exception as e:
        print(f"💥 Exception occurred: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_imperial()
