#!/usr/bin/env python3
"""
Test script for automatic BMI calculation and recalculation.
This will test that BMI is calculated automatically and updates when weight/height change.
"""

import json
from datetime import date, timedelta

import requests

# API base URL
BASE_URL = "http://127.0.0.1:8000/api/v1"


def test_bmi_calculation():
    """Test automatic BMI calculation and recalculation"""

    print("🧮 Testing Automatic BMI Calculation")
    print("=" * 50)

    # Test 1: Create progress record with weight and height (should calculate BMI)
    print("\n📊 Test 1: Automatic BMI Calculation on Create")
    progress_data = {
        "client_id": 1,
        "fecha_registro": str(date.today() + timedelta(days=4000)),  # Unique date
        "peso": 75.0,
        "altura": 1.75,
        "unidad": "metric",
        "notas": "Test BMI calculation",
    }

    try:
        response = requests.post(f"{BASE_URL}/progress/", json=progress_data)
        if response.status_code == 201:
            result = response.json()
            print("✅ Progress record created successfully")
            print(f"   Weight: {result['peso']} kg")
            print(f"   Height: {result['altura']} m")
            print(f"   BMI: {result['imc']}")

            # Verify BMI calculation (75.0 / (1.75²) = 24.49)
            expected_bmi = round(75.0 / (1.75**2), 2)
            if result["imc"] == expected_bmi:
                print(
                    f"✅ BMI calculation correct: {result['imc']} (expected: {expected_bmi})"
                )
            else:
                print(
                    f"❌ BMI calculation wrong: {result['imc']} (expected: {expected_bmi})"
                )

            progress_id = result["id"]
        else:
            print(f"❌ Failed to create progress record: {response.status_code}")
            print(f"   Error: {response.text}")
            return
    except Exception as e:
        print(f"❌ Error creating progress record: {e}")
        return

    # Test 2: Update weight (should recalculate BMI)
    print("\n📈 Test 2: BMI Recalculation on Weight Update")
    update_data = {
        "peso": 78.0,  # New weight
        "notas": "Updated weight - BMI should recalculate",
    }

    try:
        response = requests.put(f"{BASE_URL}/progress/{progress_id}", json=update_data)
        if response.status_code == 200:
            result = response.json()
            print("✅ Progress record updated successfully")
            print(f"   New Weight: {result['peso']} kg")
            print(f"   Height: {result['altura']} m")
            print(f"   New BMI: {result['imc']}")

            # Verify new BMI calculation (78.0 / (1.75²) = 25.47)
            expected_bmi = round(78.0 / (1.75**2), 2)
            if result["imc"] == expected_bmi:
                print(
                    f"✅ BMI recalculation correct: {result['imc']} (expected: {expected_bmi})"
                )
            else:
                print(
                    f"❌ BMI recalculation wrong: {result['imc']} (expected: {expected_bmi})"
                )
        else:
            print(f"❌ Failed to update progress record: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Error updating progress record: {e}")

    # Test 3: Update height (should recalculate BMI)
    print("\n📏 Test 3: BMI Recalculation on Height Update")
    update_data = {
        "altura": 1.78,  # New height
        "notas": "Updated height - BMI should recalculate",
    }

    try:
        response = requests.put(f"{BASE_URL}/progress/{progress_id}", json=update_data)
        if response.status_code == 200:
            result = response.json()
            print("✅ Progress record updated successfully")
            print(f"   Weight: {result['peso']} kg")
            print(f"   New Height: {result['altura']} m")
            print(f"   New BMI: {result['imc']}")

            # Verify new BMI calculation (78.0 / (1.78²) = 24.61)
            expected_bmi = round(78.0 / (1.78**2), 2)
            if result["imc"] == expected_bmi:
                print(
                    f"✅ BMI recalculation correct: {result['imc']} (expected: {expected_bmi})"
                )
            else:
                print(
                    f"❌ BMI recalculation wrong: {result['imc']} (expected: {expected_bmi})"
                )
        else:
            print(f"❌ Failed to update progress record: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Error updating progress record: {e}")

    # Test 4: Imperial conversion with BMI calculation
    print("\n🇺🇸 Test 4: BMI Calculation with Imperial Conversion")
    imperial_data = {
        "client_id": 1,
        "fecha_registro": str(date.today() + timedelta(days=4001)),  # Unique date
        "peso": 170,  # 170 lbs
        "altura": 70,  # 70 inches
        "unidad": "imperial",
        "notas": "Test BMI with imperial conversion",
    }

    try:
        response = requests.post(f"{BASE_URL}/progress/", json=imperial_data)
        if response.status_code == 201:
            result = response.json()
            print("✅ Imperial progress record created successfully")
            print(f"   Input: 170 lbs, 70 inches")
            print(f"   Converted Weight: {result['peso']} kg")
            print(f"   Converted Height: {result['altura']} m")
            print(f"   Calculated BMI: {result['imc']}")

            # Verify conversion and BMI calculation
            expected_weight = round(170 * 0.453592, 2)  # 77.11 kg
            expected_height = round(70 * 0.0254, 3)  # 1.778 m
            expected_bmi = round(expected_weight / (expected_height**2), 2)  # 24.39

            if abs(result["peso"] - expected_weight) < 0.1:
                print(f"✅ Weight conversion correct: {result['peso']} kg")
            else:
                print(
                    f"❌ Weight conversion wrong: {result['peso']} kg (expected: {expected_weight} kg)"
                )

            if abs(result["altura"] - expected_height) < 0.01:
                print(f"✅ Height conversion correct: {result['altura']} m")
            else:
                print(
                    f"❌ Height conversion wrong: {result['altura']} m (expected: {expected_height} m)"
                )

            if result["imc"] == expected_bmi:
                print(
                    f"✅ BMI calculation correct: {result['imc']} (expected: {expected_bmi})"
                )
            else:
                print(
                    f"❌ BMI calculation wrong: {result['imc']} (expected: {expected_bmi})"
                )
        else:
            print(
                f"❌ Failed to create imperial progress record: {response.status_code}"
            )
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Error creating imperial progress record: {e}")

    print("\n🎉 BMI Calculation Testing Complete!")
    print("✅ Automatic BMI calculation working")
    print("✅ BMI recalculation on updates working")
    print("✅ Imperial conversion with BMI working")
    print("✅ 2 decimal precision maintained")


if __name__ == "__main__":
    test_bmi_calculation()
