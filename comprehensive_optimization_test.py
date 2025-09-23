#!/usr/bin/env python3
"""
Comprehensive test for Court Allocation Optimization feature
Tests scenarios that properly demonstrate the optimization working
"""

import requests
import json

BACKEND_URL = "https://match-scheduler-11.preview.emergentagent.com/api"

def test_optimization_comprehensive():
    session = requests.Session()
    
    print("🏓 COMPREHENSIVE COURT ALLOCATION OPTIMIZATION TEST")
    print("=" * 70)
    
    def setup_players(player_count_per_category):
        """Setup players with specified count per category"""
        # Reset and clear
        session.post(f"{BACKEND_URL}/session/reset")
        
        # Delete existing players
        players_response = session.get(f"{BACKEND_URL}/players")
        if players_response.status_code == 200:
            existing_players = players_response.json()
            for player in existing_players:
                session.delete(f"{BACKEND_URL}/players/{player['id']}")
        
        # Create new players
        categories = ["Beginner", "Intermediate", "Advanced"]
        names = ["Alice", "Bob", "Carol", "David", "Emma", "Frank", "Grace", "Henry", 
                "Ivy", "Jack", "Kate", "Liam", "Mike", "Nancy", "Oscar", "Paula",
                "Quinn", "Rachel", "Steve", "Tina", "Uma", "Victor", "Wendy", "Xavier"]
        
        player_index = 0
        for category in categories:
            for i in range(player_count_per_category):
                if player_index < len(names):
                    player_data = {
                        "name": f"{names[player_index]} {category[0]}{i+1}",
                        "category": category
                    }
                    session.post(f"{BACKEND_URL}/players", json=player_data)
                    player_index += 1
        
        total_players = player_count_per_category * 3
        print(f"✅ Setup: {total_players} players ({player_count_per_category} per category)")
        return total_players
    
    def test_scenario(name, players_per_category, courts, optimization_enabled):
        """Test a specific scenario"""
        print(f"\n--- {name} ---")
        
        total_players = setup_players(players_per_category)
        
        config = {
            "numCourts": courts,
            "playSeconds": 720,
            "bufferSeconds": 30,
            "allowSingles": True,
            "allowDoubles": True,
            "allowCrossCategory": False,
            "maximizeCourtUsage": optimization_enabled
        }
        
        session.post(f"{BACKEND_URL}/session/reset")
        session.put(f"{BACKEND_URL}/session/config", json=config)
        start_response = session.post(f"{BACKEND_URL}/session/start")
        
        if start_response.status_code == 200:
            matches_response = session.get(f"{BACKEND_URL}/matches")
            if matches_response.status_code == 200:
                matches = matches_response.json()
                courts_used = len(set(match["courtIndex"] for match in matches))
                utilization = (courts_used / courts) * 100
                
                print(f"Players: {total_players} | Courts Available: {courts}")
                print(f"Courts Used: {courts_used} | Utilization: {utilization:.1f}%")
                print(f"Matches Created: {len(matches)}")
                print(f"Optimization: {'ON' if optimization_enabled else 'OFF'}")
                
                # Analyze match distribution
                category_analysis = {}
                for match in matches:
                    cat = match["category"]
                    match_type = match["matchType"]
                    if cat not in category_analysis:
                        category_analysis[cat] = {"doubles": 0, "singles": 0}
                    category_analysis[cat][match_type] += 1
                
                print(f"Match Distribution: {category_analysis}")
                
                return courts_used, len(matches), utilization
        
        return 0, 0, 0
    
    # Test scenarios that demonstrate optimization
    
    # Scenario 1: 18 players (6 per category), 6 courts
    print("\n" + "="*70)
    print("SCENARIO COMPARISON: 18 players, 6 courts")
    print("="*70)
    
    courts_off, matches_off, util_off = test_scenario(
        "18 players, 6 courts, Optimization OFF", 6, 6, False
    )
    
    courts_on, matches_on, util_on = test_scenario(
        "18 players, 6 courts, Optimization ON", 6, 6, True
    )
    
    print(f"\n📊 COMPARISON RESULTS:")
    print(f"Optimization OFF: {courts_off} courts ({util_off:.1f}%), {matches_off} matches")
    print(f"Optimization ON:  {courts_on} courts ({util_on:.1f}%), {matches_on} matches")
    
    if courts_on > courts_off:
        print("✅ OPTIMIZATION WORKING: More courts used when enabled!")
    else:
        print("❌ OPTIMIZATION NOT WORKING: Same court usage")
    
    # Scenario 2: 15 players (5 per category), 8 courts
    print("\n" + "="*70)
    print("SCENARIO COMPARISON: 15 players, 8 courts")
    print("="*70)
    
    courts_off2, matches_off2, util_off2 = test_scenario(
        "15 players, 8 courts, Optimization OFF", 5, 8, False
    )
    
    courts_on2, matches_on2, util_on2 = test_scenario(
        "15 players, 8 courts, Optimization ON", 5, 8, True
    )
    
    print(f"\n📊 COMPARISON RESULTS:")
    print(f"Optimization OFF: {courts_off2} courts ({util_off2:.1f}%), {matches_off2} matches")
    print(f"Optimization ON:  {courts_on2} courts ({util_on2:.1f}%), {matches_on2} matches")
    
    if courts_on2 > courts_off2:
        print("✅ OPTIMIZATION WORKING: More courts used when enabled!")
    else:
        print("❌ OPTIMIZATION NOT WORKING: Same court usage")
    
    # Scenario 3: Edge case - 21 players (7 per category), 10 courts
    print("\n" + "="*70)
    print("SCENARIO COMPARISON: 21 players, 10 courts")
    print("="*70)
    
    courts_off3, matches_off3, util_off3 = test_scenario(
        "21 players, 10 courts, Optimization OFF", 7, 10, False
    )
    
    courts_on3, matches_on3, util_on3 = test_scenario(
        "21 players, 10 courts, Optimization ON", 7, 10, True
    )
    
    print(f"\n📊 COMPARISON RESULTS:")
    print(f"Optimization OFF: {courts_off3} courts ({util_off3:.1f}%), {matches_off3} matches")
    print(f"Optimization ON:  {courts_on3} courts ({util_on3:.1f}%), {matches_on3} matches")
    
    if courts_on3 > courts_off3:
        print("✅ OPTIMIZATION WORKING: More courts used when enabled!")
    else:
        print("❌ OPTIMIZATION NOT WORKING: Same court usage")
    
    # Summary
    print("\n" + "="*70)
    print("🏆 FINAL OPTIMIZATION TEST SUMMARY")
    print("="*70)
    
    working_scenarios = 0
    total_scenarios = 3
    
    if courts_on > courts_off:
        working_scenarios += 1
        print("✅ Scenario 1 (18 players, 6 courts): OPTIMIZATION WORKING")
    else:
        print("❌ Scenario 1 (18 players, 6 courts): OPTIMIZATION NOT WORKING")
    
    if courts_on2 > courts_off2:
        working_scenarios += 1
        print("✅ Scenario 2 (15 players, 8 courts): OPTIMIZATION WORKING")
    else:
        print("❌ Scenario 2 (15 players, 8 courts): OPTIMIZATION NOT WORKING")
    
    if courts_on3 > courts_off3:
        working_scenarios += 1
        print("✅ Scenario 3 (21 players, 10 courts): OPTIMIZATION WORKING")
    else:
        print("❌ Scenario 3 (21 players, 10 courts): OPTIMIZATION NOT WORKING")
    
    print(f"\nOptimization Success Rate: {working_scenarios}/{total_scenarios} scenarios")
    
    if working_scenarios >= 2:
        print("🎉 COURT ALLOCATION OPTIMIZATION FEATURE IS WORKING!")
    else:
        print("⚠️  COURT ALLOCATION OPTIMIZATION NEEDS INVESTIGATION")

if __name__ == "__main__":
    test_optimization_comprehensive()