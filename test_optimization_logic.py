#!/usr/bin/env python3
"""
Test to understand the optimization logic issue
"""

import requests
import json

BACKEND_URL = "https://courtmanager.preview.emergentagent.com/api"

def test_optimization_logic():
    session = requests.Session()
    
    print("🔍 TESTING OPTIMIZATION LOGIC UNDERSTANDING")
    print("=" * 60)
    
    # Reset and setup
    session.post(f"{BACKEND_URL}/session/reset")
    
    # Delete all existing players
    players_response = session.get(f"{BACKEND_URL}/players")
    if players_response.status_code == 200:
        existing_players = players_response.json()
        for player in existing_players:
            session.delete(f"{BACKEND_URL}/players/{player['id']}")
    
    # Create a scenario where optimization should clearly work:
    # 8 players in ONE category, 6 courts available
    # Without optimization: 1 doubles match (4 players), 4 players sit
    # With optimization: 2 doubles matches (8 players), 0 players sit
    
    test_players = [
        {"name": "Player1", "category": "Beginner"},
        {"name": "Player2", "category": "Beginner"},
        {"name": "Player3", "category": "Beginner"},
        {"name": "Player4", "category": "Beginner"},
        {"name": "Player5", "category": "Beginner"},
        {"name": "Player6", "category": "Beginner"},
        {"name": "Player7", "category": "Beginner"},
        {"name": "Player8", "category": "Beginner"},
    ]
    
    for player_data in test_players:
        session.post(f"{BACKEND_URL}/players", json=player_data)
    
    print("✅ Created 8 players in Beginner category")
    
    # Test WITHOUT optimization
    print("\n--- Test WITHOUT optimization ---")
    config_off = {
        "numCourts": 6,
        "playSeconds": 720,
        "bufferSeconds": 30,
        "allowSingles": True,
        "allowDoubles": True,
        "allowCrossCategory": False,
        "maximizeCourtUsage": False
    }
    
    session.post(f"{BACKEND_URL}/session/reset")
    session.put(f"{BACKEND_URL}/session/config", json=config_off)
    start_response = session.post(f"{BACKEND_URL}/session/start")
    
    if start_response.status_code == 200:
        matches_response = session.get(f"{BACKEND_URL}/matches")
        players_response = session.get(f"{BACKEND_URL}/players")
        
        if matches_response.status_code == 200:
            matches = matches_response.json()
            players = players_response.json()
            
            courts_used = len(set(match["courtIndex"] for match in matches))
            
            # Count players in matches
            players_in_matches = set()
            for match in matches:
                players_in_matches.update(match["teamA"] + match["teamB"])
            
            players_sitting = len(players) - len(players_in_matches)
            
            print(f"Courts used: {courts_used}/6")
            print(f"Matches created: {len(matches)}")
            print(f"Players playing: {len(players_in_matches)}")
            print(f"Players sitting: {players_sitting}")
            
            for i, match in enumerate(matches):
                print(f"  Match {i+1}: {match['matchType']} on court {match['courtIndex']}")
    
    # Test WITH optimization
    print("\n--- Test WITH optimization ---")
    config_on = config_off.copy()
    config_on["maximizeCourtUsage"] = True
    
    session.post(f"{BACKEND_URL}/session/reset")
    session.put(f"{BACKEND_URL}/session/config", json=config_on)
    start_response = session.post(f"{BACKEND_URL}/session/start")
    
    if start_response.status_code == 200:
        matches_response = session.get(f"{BACKEND_URL}/matches")
        players_response = session.get(f"{BACKEND_URL}/players")
        
        if matches_response.status_code == 200:
            matches = matches_response.json()
            players = players_response.json()
            
            courts_used = len(set(match["courtIndex"] for match in matches))
            
            # Count players in matches
            players_in_matches = set()
            for match in matches:
                players_in_matches.update(match["teamA"] + match["teamB"])
            
            players_sitting = len(players) - len(players_in_matches)
            
            print(f"Courts used: {courts_used}/6")
            print(f"Matches created: {len(matches)}")
            print(f"Players playing: {len(players_in_matches)}")
            print(f"Players sitting: {players_sitting}")
            
            for i, match in enumerate(matches):
                print(f"  Match {i+1}: {match['matchType']} on court {match['courtIndex']}")
            
            # Expected result: 2 doubles matches, 8 players playing, 0 sitting
            if len(matches) > 1:
                print("✅ OPTIMIZATION WORKING: Multiple matches created!")
            else:
                print("❌ OPTIMIZATION NOT WORKING: Still only 1 match")

if __name__ == "__main__":
    test_optimization_logic()