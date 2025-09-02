#!/usr/bin/env python3
"""
Debug the algorithm step by step
"""

import requests
import json

BACKEND_URL = "https://courtmanager.preview.emergentagent.com/api"

def debug_algorithm():
    session = requests.Session()
    
    print("🔍 DEBUGGING ALGORITHM STEP BY STEP")
    print("=" * 50)
    
    # Setup 8 players in one category
    session.post(f"{BACKEND_URL}/session/reset")
    
    # Delete existing players
    players_response = session.get(f"{BACKEND_URL}/players")
    if players_response.status_code == 200:
        existing_players = players_response.json()
        for player in existing_players:
            session.delete(f"{BACKEND_URL}/players/{player['id']}")
    
    # Create 8 players
    for i in range(8):
        player_data = {"name": f"Player{i+1}", "category": "Beginner"}
        session.post(f"{BACKEND_URL}/players", json=player_data)
    
    print("✅ Created 8 players in Beginner category")
    
    # Configure with optimization ON
    config = {
        "numCourts": 6,
        "playSeconds": 720,
        "bufferSeconds": 30,
        "allowSingles": True,
        "allowDoubles": True,
        "allowCrossCategory": False,
        "maximizeCourtUsage": True
    }
    
    session.put(f"{BACKEND_URL}/session/config", json=config)
    
    # Check session config
    session_response = session.get(f"{BACKEND_URL}/session")
    if session_response.status_code == 200:
        session_data = session_response.json()
        config_data = session_data.get("config", {})
        print(f"✅ Configuration set:")
        print(f"   numCourts: {config_data.get('numCourts')}")
        print(f"   maximizeCourtUsage: {config_data.get('maximizeCourtUsage')}")
        print(f"   allowDoubles: {config_data.get('allowDoubles')}")
        print(f"   allowSingles: {config_data.get('allowSingles')}")
    
    # Start session and analyze
    print("\n--- Starting session ---")
    start_response = session.post(f"{BACKEND_URL}/session/start")
    
    if start_response.status_code == 200:
        data = start_response.json()
        print(f"✅ Session started: {data}")
        
        # Get matches
        matches_response = session.get(f"{BACKEND_URL}/matches")
        if matches_response.status_code == 200:
            matches = matches_response.json()
            
            print(f"\n📊 RESULTS:")
            print(f"Matches created: {len(matches)}")
            
            if matches:
                courts_used = set()
                for i, match in enumerate(matches):
                    courts_used.add(match["courtIndex"])
                    print(f"  Match {i+1}:")
                    print(f"    Court: {match['courtIndex']}")
                    print(f"    Category: {match['category']}")
                    print(f"    Type: {match['matchType']}")
                    print(f"    Team A: {len(match['teamA'])} players")
                    print(f"    Team B: {len(match['teamB'])} players")
                
                print(f"\nCourts used: {len(courts_used)} out of 6")
                
                # Count players in matches
                all_players_in_matches = set()
                for match in matches:
                    all_players_in_matches.update(match["teamA"] + match["teamB"])
                
                print(f"Players playing: {len(all_players_in_matches)} out of 8")
                print(f"Players sitting: {8 - len(all_players_in_matches)}")
                
                # Expected: 2 matches, 8 players playing, 0 sitting
                if len(matches) == 2:
                    print("✅ EXPECTED RESULT: 2 matches created!")
                elif len(matches) == 1:
                    print("❌ PROBLEM: Only 1 match created (expected 2)")
                else:
                    print(f"❓ UNEXPECTED: {len(matches)} matches created")
            else:
                print("❌ No matches created")
    else:
        print(f"❌ Failed to start session: {start_response.status_code} - {start_response.text}")

if __name__ == "__main__":
    debug_algorithm()