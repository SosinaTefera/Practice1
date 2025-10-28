#!/usr/bin/env python3
"""
Test script to update clients with real data and test the search/filtering system.
This will add training goals and gender to test clients so filters show actual results.
"""

import json
from datetime import date

import requests

# API base URL
BASE_URL = "http://127.0.0.1:8000/api/v1"


def update_clients_with_real_data():
    """Update test clients with training goals and gender"""

    print("🔧 Updating Test Clients with Real Data")
    print("=" * 50)

    # Client updates with real data
    client_updates = [
        {
            "id": 1,
            "nombre": "John",
            "apellidos": "Doe",
            "sexo": "Masculino",
            "objetivo_entrenamiento": "Pérdida de peso",
            "experiencia": "Baja",
        },
        {
            "id": 2,
            "nombre": "Jane",
            "apellidos": "Smith",
            "sexo": "Femenino",
            "objetivo_entrenamiento": "Aumentar masa muscular",
            "experiencia": "Media",
        },
        {
            "id": 3,
            "nombre": "Bob",
            "apellidos": "Johnson",
            "sexo": "Masculino",
            "objetivo_entrenamiento": "Rendimiento deportivo",
            "experiencia": "Alta",
        },
        {
            "id": 4,
            "nombre": "Juan",
            "apellidos": "García",
            "sexo": "Masculino",
            "objetivo_entrenamiento": "Pérdida de peso",
            "experiencia": "Baja",
        },
    ]

    print("📝 Updating clients with training goals and gender...")

    for client_data in client_updates:
        client_id = client_data["id"]
        update_data = {k: v for k, v in client_data.items() if k != "id"}

        try:
            response = requests.put(f"{BASE_URL}/clients/{client_id}", json=update_data)
            if response.status_code == 200:
                print(
                    f"✅ Updated client {client_id}: {client_data['nombre']} {client_data['apellidos']}"
                )
                print(f"   - Gender: {client_data['sexo']}")
                print(f"   - Goal: {client_data['objetivo_entrenamiento']}")
                print(f"   - Experience: {client_data['experiencia']}")
            else:
                print(f"❌ Failed to update client {client_id}: {response.status_code}")
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"❌ Error updating client {client_id}: {e}")

        print()  # Empty line for readability

    print("🎉 Client updates completed!")


def test_filters_with_real_data():
    """Test all filters now that clients have real data"""

    print("\n🧪 Testing Filters with Real Data")
    print("=" * 50)

    # Test 1: Training Goal Filters
    print("\n🎯 Test 1: Training Goal Filters")
    print("-" * 30)

    goals = ["Pérdida de peso", "Aumentar masa muscular", "Rendimiento deportivo"]
    for goal in goals:
        try:
            response = requests.get(
                f"{BASE_URL}/clients/search?training_goal={goal}&limit=5"
            )
            if response.status_code == 200:
                clients = response.json()
                print(f"✅ {goal}: {len(clients)} clients")
                for client in clients:
                    print(f"   - {client['nombre']} {client['apellidos']}")
            else:
                print(f"❌ {goal}: Failed with status {response.status_code}")
        except Exception as e:
            print(f"❌ {goal}: Error - {e}")

    # Test 2: Gender Filters
    print("\n👥 Test 2: Gender Filters")
    print("-" * 30)

    genders = ["Masculino", "Femenino"]
    for gender in genders:
        try:
            response = requests.get(
                f"{BASE_URL}/clients/search?gender={gender}&limit=5"
            )
            if response.status_code == 200:
                clients = response.json()
                print(f"✅ {gender}: {len(clients)} clients")
                for client in clients:
                    print(f"   - {client['nombre']} {client['apellidos']}")
            else:
                print(f"❌ {gender}: Failed with status {response.status_code}")
        except Exception as e:
            print(f"❌ {gender}: Error - {e}")

    # Test 3: Experience Filters
    print("\n📚 Test 3: Experience Level Filters")
    print("-" * 30)

    experiences = ["Baja", "Media", "Alta"]
    for exp in experiences:
        try:
            response = requests.get(
                f"{BASE_URL}/clients/search?experience={exp}&limit=5"
            )
            if response.status_code == 200:
                clients = response.json()
                print(f"✅ {exp}: {len(clients)} clients")
                for client in clients:
                    print(f"   - {client['nombre']} {client['apellidos']}")
            else:
                print(f"❌ {exp}: Failed with status {response.status_code}")
        except Exception as e:
            print(f"❌ {exp}: Error - {e}")

    # Test 4: Combined Filters
    print("\n🔍 Test 4: Combined Filters")
    print("-" * 30)

    try:
        # Male clients with weight loss goal
        response = requests.get(
            f"{BASE_URL}/clients/search?gender=Masculino&training_goal=Pérdida de peso&limit=5"
        )
        if response.status_code == 200:
            clients = response.json()
            print(f"✅ Male + Weight Loss: {len(clients)} clients")
            for client in clients:
                print(f"   - {client['nombre']} {client['apellidos']}")
        else:
            print(f"❌ Combined filter failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Combined filter error: {e}")


if __name__ == "__main__":
    print("🚀 Nexia Client Data Update & Filter Testing")
    print("=" * 60)

    # Step 1: Update clients with real data
    update_clients_with_real_data()

    # Step 2: Test filters with real data
    test_filters_with_real_data()

    print("\n🎉 All testing completed!")
    print("Now your search and filtering system has real data to work with!")
