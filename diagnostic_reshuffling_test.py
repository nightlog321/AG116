#!/usr/bin/env python3
"""
Diagnostic test for Enhanced Player Reshuffling Algorithm
Detailed analysis of what's happening with the reshuffling
"""

import requests
import json

# Backend URL from environment
BACKEND_URL = "https://court-timer.preview.emergentagent.com/api"

def test_detailed_reshuffling():
    """Detailed diagnostic test"""
    session = requests.Session()
    
    print("🔍 DIAGNOSTIC TEST: Enhanced Player Reshuffling Algorithm")
    print("=" * 60)
    
    # Step 1: Setup environment
    print("\n1. Setting up test environment...")
    response = session.post(f"{BACKEND_URL}/add-test-data")
    if response.status_code == 200:
        print("✅ Test data added successfully")
    else:
        print(f"❌ Failed to add test data: {response.status_code}")
        return
    
    # Step 2: Check initial players
    print("\n2. Checking initial players...")
    response = session.get(f"{BACKEND_URL}/players")
    if response.status_code == 200:
        players = response.json()
        print(f"✅ Found {len(players)} players")
        for i, player in enumerate(players[:5]):  # Show first 5
            print(f"   Player {i+1}: {player['name']} ({player['category']}, Rating: {player['rating']})")
    else:
        print(f"❌ Failed to get players: {response.status_code}")
        return
    
    # Step 3: Check initial session state
    print("\n3. Checking initial session state...")
    response = session.get(f"{BACKEND_URL}/session")
    if response.status_code == 200:
        session_data = response.json()
        print(f"✅ Session phase: {session_data['phase']}, Round: {session_data['currentRound']}")
        histories = session_data.get('histories', {})
        print(f"   Partner history entries: {len(histories.get('partnerHistory', {}))}")
        print(f"   Opponent history entries: {len(histories.get('opponentHistory', {}))}")
    else:
        print(f"❌ Failed to get session: {response.status_code}")
        return
    
    # Step 4: Generate Round 1
    print("\n4. Generating Round 1...")
    response = session.post(f"{BACKEND_URL}/session/generate-matches")
    if response.status_code == 200:
        session_data = response.json()
        print(f"✅ Round 1 generated - Phase: {session_data['phase']}, Round: {session_data['currentRound']}")
    else:
        print(f"❌ Failed to generate Round 1: {response.status_code}")
        print(f"   Response: {response.text}")
        return
    
    # Step 5: Check Round 1 matches
    print("\n5. Checking Round 1 matches...")
    response = session.get(f"{BACKEND_URL}/matches")
    if response.status_code == 200:
        matches = response.json()
        round1_matches = [m for m in matches if m['roundIndex'] == 1]
        print(f"✅ Found {len(round1_matches)} matches for Round 1")
        
        for i, match in enumerate(round1_matches):
            print(f"   Match {i+1}: Court {match['courtIndex']}, {match['category']}")
            print(f"     Team A: {match['teamA']} vs Team B: {match['teamB']}")
            print(f"     Type: {match['matchType']}, Status: {match['status']}")
    else:
        print(f"❌ Failed to get matches: {response.status_code}")
        return
    
    # Step 6: Start session
    print("\n6. Starting session...")
    response = session.post(f"{BACKEND_URL}/session/start")
    if response.status_code == 200:
        session_data = response.json()
        print(f"✅ Session started - Phase: {session_data['phase']}, Round: {session_data['currentRound']}")
    else:
        print(f"❌ Failed to start session: {response.status_code}")
        print(f"   Response: {response.text}")
        return
    
    # Step 7: Generate Round 2
    print("\n7. Generating Round 2...")
    response = session.post(f"{BACKEND_URL}/session/next-round")
    if response.status_code == 200:
        session_data = response.json()
        print(f"✅ Round 2 generated - Phase: {session_data['phase']}, Round: {session_data['currentRound']}")
    else:
        print(f"❌ Failed to generate Round 2: {response.status_code}")
        print(f"   Response: {response.text}")
        return
    
    # Step 8: Check Round 2 matches
    print("\n8. Checking Round 2 matches...")
    response = session.get(f"{BACKEND_URL}/matches")
    if response.status_code == 200:
        matches = response.json()
        round2_matches = [m for m in matches if m['roundIndex'] == 2]
        print(f"✅ Found {len(round2_matches)} matches for Round 2")
        
        if len(round2_matches) == 0:
            print("❌ CRITICAL ISSUE: No matches generated for Round 2!")
            print("   This indicates the reshuffling algorithm is not creating new matches")
        else:
            for i, match in enumerate(round2_matches):
                print(f"   Match {i+1}: Court {match['courtIndex']}, {match['category']}")
                print(f"     Team A: {match['teamA']} vs Team B: {match['teamB']}")
                print(f"     Type: {match['matchType']}, Status: {match['status']}")
    else:
        print(f"❌ Failed to get matches: {response.status_code}")
        return
    
    # Step 9: Check session histories after Round 2
    print("\n9. Checking session histories after Round 2...")
    response = session.get(f"{BACKEND_URL}/session")
    if response.status_code == 200:
        session_data = response.json()
        histories = session_data.get('histories', {})
        partner_history = histories.get('partnerHistory', {})
        opponent_history = histories.get('opponentHistory', {})
        
        print(f"✅ Partner history entries: {len(partner_history)}")
        print(f"✅ Opponent history entries: {len(opponent_history)}")
        
        if len(partner_history) == 0 and len(opponent_history) == 0:
            print("❌ CRITICAL ISSUE: No history tracking data found!")
            print("   This indicates the history tracking is not working")
        else:
            print("   Sample partner history:")
            for player_id, partners in list(partner_history.items())[:2]:
                print(f"     Player {player_id}: {partners}")
            
            print("   Sample opponent history:")
            for player_id, opponents in list(opponent_history.items())[:2]:
                print(f"     Player {player_id}: {opponents}")
    else:
        print(f"❌ Failed to get session: {response.status_code}")
        return
    
    # Step 10: Compare Round 1 vs Round 2 teams
    print("\n10. Comparing Round 1 vs Round 2 teams...")
    response = session.get(f"{BACKEND_URL}/matches")
    if response.status_code == 200:
        matches = response.json()
        round1_matches = [m for m in matches if m['roundIndex'] == 1]
        round2_matches = [m for m in matches if m['roundIndex'] == 2]
        
        round1_teams = set()
        for match in round1_matches:
            team_a = tuple(sorted(match['teamA']))
            team_b = tuple(sorted(match['teamB']))
            round1_teams.add(team_a)
            round1_teams.add(team_b)
        
        round2_teams = set()
        for match in round2_matches:
            team_a = tuple(sorted(match['teamA']))
            team_b = tuple(sorted(match['teamB']))
            round2_teams.add(team_a)
            round2_teams.add(team_b)
        
        identical_teams = len(round1_teams & round2_teams)
        total_teams = len(round1_teams | round2_teams)
        
        print(f"✅ Round 1 teams: {len(round1_teams)}")
        print(f"✅ Round 2 teams: {len(round2_teams)}")
        print(f"✅ Identical teams: {identical_teams}")
        print(f"✅ Total unique teams: {total_teams}")
        
        if len(round2_teams) == 0:
            print("❌ CRITICAL ISSUE: No teams in Round 2 - matches not being created!")
        elif identical_teams == len(round1_teams) and len(round1_teams) == len(round2_teams):
            print("❌ CRITICAL ISSUE: All teams are identical - no reshuffling happening!")
        else:
            reshuffling_effectiveness = 1.0 - (identical_teams / total_teams) if total_teams > 0 else 0
            print(f"✅ Reshuffling effectiveness: {reshuffling_effectiveness:.2%}")
    
    print("\n" + "=" * 60)
    print("🏁 DIAGNOSTIC TEST COMPLETE")

if __name__ == "__main__":
    test_detailed_reshuffling()