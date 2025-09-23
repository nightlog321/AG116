#!/usr/bin/env python3
"""
Detailed Format System Analysis
Analyzes the actual behavior of the new format system
"""

import requests
import json

BACKEND_URL = "https://match-scheduler-11.preview.emergentagent.com/api"

def test_detailed_scenarios():
    session = requests.Session()
    
    print("🔍 DETAILED FORMAT SYSTEM ANALYSIS")
    print("=" * 50)
    
    # Reset and setup
    session.post(f"{BACKEND_URL}/init")
    session.post(f"{BACKEND_URL}/session/reset")
    
    # Create exactly 8 players (2 per category, plus 2 extra)
    test_players = [
        {"name": "Player1", "category": "Beginner"},
        {"name": "Player2", "category": "Beginner"},
        {"name": "Player3", "category": "Intermediate"},
        {"name": "Player4", "category": "Intermediate"},
        {"name": "Player5", "category": "Advanced"},
        {"name": "Player6", "category": "Advanced"},
        {"name": "Player7", "category": "Beginner"},
        {"name": "Player8", "category": "Intermediate"}
    ]
    
    for player in test_players:
        session.post(f"{BACKEND_URL}/players", json=player)
    
    print(f"Created {len(test_players)} players")
    
    # Test Scenario 1: Both formats enabled
    print("\n--- Scenario 1: Both Formats Enabled ---")
    config = {
        "numCourts": 6,
        "playSeconds": 720,
        "bufferSeconds": 30,
        "allowSingles": True,
        "allowDoubles": True,
        "allowCrossCategory": False
    }
    
    session.put(f"{BACKEND_URL}/session/config", json=config)
    session.post(f"{BACKEND_URL}/session/start")
    
    # Analyze matches
    matches_response = session.get(f"{BACKEND_URL}/matches")
    players_response = session.get(f"{BACKEND_URL}/players")
    
    if matches_response.status_code == 200 and players_response.status_code == 200:
        matches = matches_response.json()
        players = players_response.json()
        
        print(f"Total matches created: {len(matches)}")
        
        # Group by category
        category_analysis = {}
        for match in matches:
            cat = match["category"]
            if cat not in category_analysis:
                category_analysis[cat] = {"doubles": 0, "singles": 0, "players": set()}
            
            category_analysis[cat][match["matchType"]] += 1
            category_analysis[cat]["players"].update(match["teamA"] + match["teamB"])
        
        # Count players per category
        player_counts = {}
        for player in players:
            cat = player["category"]
            player_counts[cat] = player_counts.get(cat, 0) + 1
        
        print("\nCategory Analysis:")
        for cat, analysis in category_analysis.items():
            players_in_matches = len(analysis["players"])
            total_players = player_counts.get(cat, 0)
            print(f"  {cat}: {analysis['doubles']} doubles, {analysis['singles']} singles")
            print(f"    Players: {players_in_matches}/{total_players} playing")
        
        # Overall statistics
        total_doubles = sum(analysis["doubles"] for analysis in category_analysis.values())
        total_singles = sum(analysis["singles"] for analysis in category_analysis.values())
        total_players_in_matches = sum(len(analysis["players"]) for analysis in category_analysis.values())
        
        print(f"\nOverall: {total_doubles} doubles, {total_singles} singles")
        print(f"Players in matches: {total_players_in_matches}/{len(players)}")
    
    # Test Scenario 2: Only doubles enabled with 6 players
    print("\n--- Scenario 2: Only Doubles, 6 Players ---")
    session.post(f"{BACKEND_URL}/session/reset")
    
    # Remove 2 players to have 6
    players_response = session.get(f"{BACKEND_URL}/players")
    if players_response.status_code == 200:
        players = players_response.json()
        for i in range(2):
            if i < len(players):
                session.delete(f"{BACKEND_URL}/players/{players[i]['id']}")
    
    config_doubles_only = {
        "numCourts": 6,
        "playSeconds": 720,
        "bufferSeconds": 30,
        "allowSingles": False,
        "allowDoubles": True,
        "allowCrossCategory": False
    }
    
    session.put(f"{BACKEND_URL}/session/config", json=config_doubles_only)
    session.post(f"{BACKEND_URL}/session/start")
    
    matches_response = session.get(f"{BACKEND_URL}/matches")
    players_response = session.get(f"{BACKEND_URL}/players")
    
    if matches_response.status_code == 200 and players_response.status_code == 200:
        matches = matches_response.json()
        players = players_response.json()
        
        print(f"Total matches created: {len(matches)}")
        
        doubles_matches = [m for m in matches if m["matchType"] == "doubles"]
        singles_matches = [m for m in matches if m["matchType"] == "singles"]
        
        print(f"Doubles matches: {len(doubles_matches)}")
        print(f"Singles matches: {len(singles_matches)}")
        
        total_players_in_matches = sum(len(m["teamA"]) + len(m["teamB"]) for m in matches)
        print(f"Players in matches: {total_players_in_matches}/{len(players)}")
        
        # Expected: With 6 players and only doubles enabled:
        # - Each category has 2 players (after removing 2)
        # - 2 players per category can't make a doubles match (need 4)
        # - So players should sit or no matches created per category
        
        # Count players per category
        player_counts = {}
        for player in players:
            cat = player["category"]
            player_counts[cat] = player_counts.get(cat, 0) + 1
        
        print("Player distribution:", player_counts)

if __name__ == "__main__":
    test_detailed_scenarios()