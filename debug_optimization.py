#!/usr/bin/env python3
"""
Debug script to investigate Court Allocation Optimization issue
"""

import requests
import json

BACKEND_URL = "https://courtmanager.preview.emergentagent.com/api"

def debug_optimization():
    session = requests.Session()
    
    print("🔍 DEBUGGING COURT ALLOCATION OPTIMIZATION")
    print("=" * 60)
    
    # Reset and setup
    session.post(f"{BACKEND_URL}/session/reset")
    
    # Delete all existing players
    players_response = session.get(f"{BACKEND_URL}/players")
    if players_response.status_code == 200:
        existing_players = players_response.json()
        for player in existing_players:
            session.delete(f"{BACKEND_URL}/players/{player['id']}")
    
    # Create exactly 12 players (4 per category)
    test_players = [
        # Beginner (4 players)
        {"name": "Alice Johnson", "category": "Beginner"},
        {"name": "Bob Smith", "category": "Beginner"},
        {"name": "Carol Davis", "category": "Beginner"},
        {"name": "David Wilson", "category": "Beginner"},
        # Intermediate (4 players)
        {"name": "Emma Brown", "category": "Intermediate"},
        {"name": "Frank Miller", "category": "Intermediate"},
        {"name": "Grace Lee", "category": "Intermediate"},
        {"name": "Henry Taylor", "category": "Intermediate"},
        # Advanced (4 players)
        {"name": "Ivy Chen", "category": "Advanced"},
        {"name": "Jack Rodriguez", "category": "Advanced"},
        {"name": "Kate Anderson", "category": "Advanced"},
        {"name": "Liam Thompson", "category": "Advanced"}
    ]
    
    for player_data in test_players:
        session.post(f"{BACKEND_URL}/players", json=player_data)
    
    print(f"✅ Created 12 players (4 per category)")
    
    # Test Scenario 1: maximizeCourtUsage=false
    print("\n--- Scenario 1: maximizeCourtUsage=false ---")
    config_false = {
        "numCourts": 6,
        "playSeconds": 720,
        "bufferSeconds": 30,
        "allowSingles": True,
        "allowDoubles": True,
        "allowCrossCategory": False,
        "maximizeCourtUsage": False
    }
    
    session.post(f"{BACKEND_URL}/session/reset")
    session.put(f"{BACKEND_URL}/session/config", json=config_false)
    start_response = session.post(f"{BACKEND_URL}/session/start")
    
    if start_response.status_code == 200:
        matches_response = session.get(f"{BACKEND_URL}/matches")
        if matches_response.status_code == 200:
            matches = matches_response.json()
            courts_used = len(set(match["courtIndex"] for match in matches))
            
            print(f"Courts used: {courts_used}/6")
            print(f"Matches created: {len(matches)}")
            
            # Analyze matches by category
            category_analysis = {}
            for match in matches:
                cat = match["category"]
                match_type = match["matchType"]
                if cat not in category_analysis:
                    category_analysis[cat] = {"doubles": 0, "singles": 0}
                category_analysis[cat][match_type] += 1
            
            print(f"Match distribution: {category_analysis}")
    
    # Test Scenario 2: maximizeCourtUsage=true
    print("\n--- Scenario 2: maximizeCourtUsage=true ---")
    config_true = config_false.copy()
    config_true["maximizeCourtUsage"] = True
    
    session.post(f"{BACKEND_URL}/session/reset")
    session.put(f"{BACKEND_URL}/session/config", json=config_true)
    start_response = session.post(f"{BACKEND_URL}/session/start")
    
    if start_response.status_code == 200:
        matches_response = session.get(f"{BACKEND_URL}/matches")
        if matches_response.status_code == 200:
            matches = matches_response.json()
            courts_used = len(set(match["courtIndex"] for match in matches))
            
            print(f"Courts used: {courts_used}/6")
            print(f"Matches created: {len(matches)}")
            
            # Analyze matches by category
            category_analysis = {}
            for match in matches:
                cat = match["category"]
                match_type = match["matchType"]
                if cat not in category_analysis:
                    category_analysis[cat] = {"doubles": 0, "singles": 0}
                category_analysis[cat][match_type] += 1
            
            print(f"Match distribution: {category_analysis}")
            
            # Show detailed match information
            print("\nDetailed match information:")
            for i, match in enumerate(matches):
                print(f"  Match {i+1}: Court {match['courtIndex']}, Category: {match['category']}, Type: {match['matchType']}")
                print(f"    Team A: {match['teamA']}")
                print(f"    Team B: {match['teamB']}")
    
    # Test Scenario 3: Different player distribution
    print("\n--- Scenario 3: 16 players (more players to test optimization) ---")
    
    # Add 4 more players
    additional_players = [
        {"name": "Mike Extra1", "category": "Beginner"},
        {"name": "Sarah Extra2", "category": "Intermediate"},
        {"name": "Tom Extra3", "category": "Advanced"},
        {"name": "Lisa Extra4", "category": "Beginner"}
    ]
    
    for player_data in additional_players:
        session.post(f"{BACKEND_URL}/players", json=player_data)
    
    session.post(f"{BACKEND_URL}/session/reset")
    session.put(f"{BACKEND_URL}/session/config", json=config_true)
    start_response = session.post(f"{BACKEND_URL}/session/start")
    
    if start_response.status_code == 200:
        matches_response = session.get(f"{BACKEND_URL}/matches")
        if matches_response.status_code == 200:
            matches = matches_response.json()
            courts_used = len(set(match["courtIndex"] for match in matches))
            
            print(f"Courts used: {courts_used}/6")
            print(f"Matches created: {len(matches)}")
            
            # Analyze matches by category
            category_analysis = {}
            for match in matches:
                cat = match["category"]
                match_type = match["matchType"]
                if cat not in category_analysis:
                    category_analysis[cat] = {"doubles": 0, "singles": 0}
                category_analysis[cat][match_type] += 1
            
            print(f"Match distribution: {category_analysis}")

if __name__ == "__main__":
    debug_optimization()