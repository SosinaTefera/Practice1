#!/usr/bin/env python3
"""
Test script for the new unit conversion system.
This will test both metric and imperial inputs to ensure conversion works correctly.
"""

import json
from datetime import date, timedelta

import requests

# API base URL
BASE_URL = "http://127.0.0.1:8000/api/v1"


def test_unit_conversion():
    """Test the unit conversion system"""

    print("🧪 Testing Unit Conversion System")
    print("=" * 50)

    # Test 1: Metric input (should work as before)
    print("\n📊 Test 1: Metric Input (Default)")
    metric_data = {
        "client_id": 1,  # Add required client_id
        "fecha_registro": str(date.today() + timedelta(days=3000)),  # Far future date
        "peso": 74.8,
        "altura": 1.75,
        "unidad": "metric",
        "notas": "Test metric input",
    }

    try:
        response = requests.post(f"{BASE_URL}/progress/", json=metric_data)
        if response.status_code == 201:
            print("✅ Metric input successful")
            result = response.json()
            print(f"   Stored weight: {result['peso']} kg")
            print(f"   Stored height: {result['altura']} m")
            print(f"   Unit: {result['unidad']}")
        else:
            print(f"❌ Metric input failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Metric test error: {e}")

    # Test 2: Imperial input (should convert automatically)
    print("\n🇺🇸 Test 2: Imperial Input (Should Convert)")
    imperial_data = {
        "client_id": 1,  # Add required client_id
        "fecha_registro": str(
            date.today() + timedelta(days=3001)
        ),  # Far future date + 1 day
        "peso": 165,  # 165 lbs
        "altura": 69,  # 69 inches
        "unidad": "imperial",
        "notas": "Test imperial input",
    }

    try:
        response = requests.post(f"{BASE_URL}/progress/", json=imperial_data)
        if response.status_code == 201:
            print("✅ Imperial input successful")
            result = response.json()
            print(f"   Input: 165 lbs, 69 inches")
            print(f"   Stored weight: {result['peso']} kg (converted)")
            print(f"   Stored height: {result['altura']} m (converted)")
            print(f"   Unit: {result['unidad']}")

            # Verify conversion
            expected_weight = round(165 * 0.453592, 2)  # 74.84 kg
            expected_height = round(69 * 0.0254, 3)  # 1.753 m

            if abs(result["peso"] - expected_weight) < 0.1:
                print("✅ Weight conversion correct")
            else:
                print(f"❌ Weight conversion wrong. Expected: {expected_weight} kg")

            if abs(result["altura"] - expected_height) < 0.01:
                print("✅ Height conversion correct")
            else:
                print(f"❌ Height conversion wrong. Expected: {expected_height} m")

        else:
            print(f"❌ Imperial input failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Imperial test error: {e}")

    # Test 3: No Unit Specified (Should Default to Metric)
    print("\n🔧 Test 3: No Unit Specified (Should Default to Metric)")
    default_data = {
        "client_id": 1,  # Add required client_id
        "fecha_registro": str(
            date.today() + timedelta(days=3002)
        ),  # Far future date + 2 days
        "peso": 80.0,
        "altura": 1.80,
        "notas": "Test default unit",
    }

    try:
        response = requests.post(f"{BASE_URL}/progress/", json=default_data)
        if response.status_code == 201:
            print("✅ Default unit test successful")
            result = response.json()
            print(f"   Stored weight: {result['peso']} kg")
            print(f"   Stored height: {result['altura']} m")
            print(f"   Unit: {result['unidad']} (should be 'metric')")
        else:
            print(f"❌ Default unit test failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Default unit test error: {e}")

    # Test 4: Get existing progress to verify no validation errors
    print("\n📋 Test 4: Retrieve Existing Progress (Should Work)")
    try:
        response = requests.get(f"{BASE_URL}/progress/?client_id=1&skip=0&limit=10")
        if response.status_code == 200:
            print("✅ Existing progress retrieval successful")
            data = response.json()
            print(f"   Retrieved {len(data)} progress records")
            for i, record in enumerate(data[:3]):  # Show first 3
                print(f"   Record {i+1}: {record['peso']} kg, {record['altura']} m")
        else:
            print(f"❌ Progress retrieval failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Progress retrieval error: {e}")

    print("\n🎉 Unit Conversion Testing Complete!")


if __name__ == "__main__":
    test_unit_conversion()
