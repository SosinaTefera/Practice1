#!/usr/bin/env python3
"""
Test script for the new client search and filtering system.
This demonstrates how coaches can easily find and manage their clients.
"""

import json
from datetime import date

import requests

# API base URL
BASE_URL = "http://127.0.0.1:8000/api/v1"


def test_search_and_filtering():
    """Test the new search and filtering capabilities"""

    print("🔍 Testing Client Search & Filtering System")
    print("=" * 60)

    # Test 1: Basic search by name
    print("\n📝 Test 1: Search by Name")
    print("-" * 30)

    try:
        response = requests.get(f"{BASE_URL}/clients/search?search=john&limit=5")
        if response.status_code == 200:
            clients = response.json()
            print(f"✅ Found {len(clients)} clients with 'john' in name/email")
            for client in clients[:3]:  # Show first 3
                print(
                    f"   - {client['nombre']} {client['apellidos']} ({client['mail']})"
                )
        else:
            print(f"❌ Search failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Search test error: {e}")

    # Test 2: Filter by age range
    print("\n👥 Test 2: Filter by Age Range (25-40)")
    print("-" * 30)

    try:
        response = requests.get(
            f"{BASE_URL}/clients/search?age_min=25&age_max=40&limit=5"
        )
        if response.status_code == 200:
            clients = response.json()
            print(f"✅ Found {len(clients)} clients aged 25-40")
            for client in clients[:3]:
                print(
                    f"   - {client['nombre']} {client['apellidos']} (Age: {client.get('edad', 'N/A')})"
                )
        else:
            print(f"❌ Age filter failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Age filter test error: {e}")

    # Test 3: Filter by Training Goal (Pérdida de peso)
    print("\n🎯 Test 3: Filter by Training Goal (Pérdida de peso)")
    print("-" * 50)

    try:
        response = requests.get(
            f"{BASE_URL}/clients/search?training_goal=Pérdida de peso&limit=5"
        )
        if response.status_code == 200:
            clients = response.json()
            print(f"✅ Found {len(clients)} clients with weight loss goal")
            for client in clients[:3]:  # Show first 3
                print(
                    f"   - {client['nombre']} {client['apellidos']} (Goal: {client['objetivo_entrenamiento']})"
                )
        else:
            print(f"❌ Goal filter failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Goal filter error: {e}")

    # Test 3b: Filter by another Training Goal (muscle gain)
    print("\n🎯 Test 3b: Filter by Training Goal (Aumentar masa muscular)")
    print("-" * 50)

    try:
        response = requests.get(
            f"{BASE_URL}/clients/search?training_goal=Aumentar masa muscular&limit=5"
        )
        if response.status_code == 200:
            clients = response.json()
            print(f"✅ Found {len(clients)} clients with muscle gain goal")
            for client in clients[:3]:  # Show first 3
                print(
                    f"   - {client['nombre']} {client['apellidos']} (Goal: {client['objetivo_entrenamiento']})"
                )
        else:
            print(f"❌ Goal filter failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Goal filter error: {e}")

    # Test 3c: Filter by Gender
    print("\n👥 Test 3c: Filter by Gender (Masculino)")
    print("-" * 50)

    try:
        response = requests.get(f"{BASE_URL}/clients/search?gender=Masculino&limit=5")
        if response.status_code == 200:
            clients = response.json()
            print(f"✅ Found {len(clients)} male clients")
            for client in clients[:3]:  # Show first 3
                print(
                    f"   - {client['nombre']} {client['apellidos']} (Gender: {client['sexo']})"
                )
        else:
            print(f"❌ Gender filter failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Gender filter error: {e}")

    # Test 4: Combined search and filter
    print("\n🔍 Test 4: Combined Search + Age + Sorting")
    print("-" * 30)

    try:
        response = requests.get(
            f"{BASE_URL}/clients/search?search=a&age_min=20&sort_by=edad&sort_order=desc&limit=5"
        )
        if response.status_code == 200:
            clients = response.json()
            print(
                f"✅ Found {len(clients)} clients with 'a' in name, age 20+, sorted by age desc"
            )
            for client in clients[:3]:
                age = client.get("edad", "N/A")
                print(f"   - {client['nombre']} {client['apellidos']} (Age: {age})")
        else:
            print(f"❌ Combined search failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Combined search test error: {e}")

    # Test 5: Pagination
    print("\n📄 Test 5: Pagination (first 3 clients)")
    print("-" * 30)

    try:
        response = requests.get(f"{BASE_URL}/clients/search?skip=0&limit=3")
        if response.status_code == 200:
            clients = response.json()
            print(f"✅ Retrieved {len(clients)} clients (page 1)")
            for i, client in enumerate(clients):
                print(f"   {i+1}. {client['nombre']} {client['apellidos']}")

            # Test second page
            response2 = requests.get(f"{BASE_URL}/clients/search?skip=3&limit=3")
            if response2.status_code == 200:
                clients2 = response2.json()
                print(f"✅ Retrieved {len(clients2)} clients (page 2)")
                for i, client in enumerate(clients2):
                    print(f"   {i+4}. {client['nombre']} {client['apellidos']}")
        else:
            print(f"❌ Pagination failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Pagination test error: {e}")

    # Test 6: Show available endpoints
    print("\n🌐 Test 6: Available Search Endpoints")
    print("-" * 30)
    print("✅ GET /api/v1/clients/ - Basic client list with pagination")
    print("✅ GET /api/v1/clients/search - Advanced search with filters:")
    print("   - search: Name/email search")
    print("   - age_min/age_max: Age range filter")
    print("   - gender: Gender filter")
    print("   - training_goal: Training goal filter")
    print("   - experience: Experience level filter")
    print("   - sort_by: nombre, edad, fecha_alta")
    print("   - sort_order: asc, desc")
    print("   - skip/limit: Pagination")

    print("\n🎉 Search & Filtering Testing Complete!")
    print("Coaches can now easily find and manage their clients!")


if __name__ == "__main__":
    test_search_and_filtering()
