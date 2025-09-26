#!/usr/bin/env python3
"""
Debug test for court allocation optimization
"""

import requests
import json

BACKEND_URL = "https://court-timer.preview.emergentagent.com/api"

def debug_court_allocation():
    session = requests.Session()
    
    print("=== DEBUGGING COURT ALLOCATION OPTIMIZATION ===")
    
    # Reset session
    session.post(f"{BACKEND_URL}/session/reset")
    
    # Clear existing players
    players_response = session.get(f"{BACKEND_URL}/players")
    if players_response.status_code == 200:
        existing_players = players_response.json()
        for player in existing_players:
            session.delete(f"{BACKEND_URL}/players/{player['id']}")
    
    # Create exactly 8 Beginner players
    test_players = [
        {"name": "Player1", "category": "Beginner"},
        {"name": "Player2", "category": "Beginner"},
        {"name": "Player3", "category": "Beginner"},
        {"name": "Player4", "category": "Beginner"},
        {"name": "Player5", "category": "Beginner"},
        {"name": "Player6", "category": "Beginner"},
        {"name": "Player7", "category": "Beginner"},
        {"name": "Player8", "category": "Beginner"}
    ]
    
    created_players = []
    for player_data in test_players:
        response = session.post(f"{BACKEND_URL}/players", json=player_data)
        if response.status_code == 200:
            created_players.append(response.json())
    
    print(f"Created {len(created_players)} players")
    
    # Configure with optimization
    config = {
        "numCourts": 6,
        "playSeconds": 720,
        "bufferSeconds": 30,
        "allowSingles": True,
        "allowDoubles": True,
        "allowCrossCategory": False,
        "maximizeCourtUsage": True
    }
    
    config_response = session.put(f"{BACKEND_URL}/session/config", json=config)
    print(f"Config response: {config_response.status_code}")
    if config_response.status_code == 200:
        print(f"Config set: {config_response.json()['config']}")
    
    # Start session
    print("\n--- Starting Session ---")
    start_response = session.post(f"{BACKEND_URL}/session/start")
    print(f"Start response: {start_response.status_code}")
    if start_response.status_code == 200:
        start_data = start_response.json()
        print(f"Start data: {start_data}")
    
    # Get matches
    print("\n--- Analyzing Matches ---")
    matches_response = session.get(f"{BACKEND_URL}/matches")
    if matches_response.status_code == 200:
        matches = matches_response.json()
        print(f"Total matches created: {len(matches)}")
        
        for i, match in enumerate(matches):
            print(f"Match {i+1}:")
            print(f"  Category: {match['category']}")
            print(f"  Type: {match['matchType']}")
            print(f"  Court: {match['courtIndex']}")
            print(f"  TeamA: {match['teamA']} ({len(match['teamA'])} players)")
            print(f"  TeamB: {match['teamB']} ({len(match['teamB'])} players)")
        
        # Count players used
        players_used = set()
        for match in matches:
            players_used.update(match["teamA"] + match["teamB"])
        
        print(f"\nPlayers used: {len(players_used)}/8")
        print(f"Players sitting: {8 - len(players_used)}")
        
        doubles_matches = [m for m in matches if m["matchType"] == "doubles"]
        print(f"Doubles matches: {len(doubles_matches)}")
        
        if len(doubles_matches) == 2 and len(players_used) == 8:
            print("✅ SUCCESS: Fix is working!")
        else:
            print("❌ FAILED: Fix is not working")
    
    # Get session state
    print("\n--- Session State ---")
    session_response = session.get(f"{BACKEND_URL}/session")
    if session_response.status_code == 200:
        session_data = session_response.json()
        print(f"Session phase: {session_data['phase']}")
        print(f"Current round: {session_data['currentRound']}")
        print(f"Config: {session_data['config']}")

if __name__ == "__main__":
    debug_court_allocation()