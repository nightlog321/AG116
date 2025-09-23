#!/usr/bin/env python3
"""
Detailed Analysis of Court Allocation Algorithm
Analyzes why court utilization is suboptimal
"""

import requests
import json

BACKEND_URL = "https://match-scheduler-11.preview.emergentagent.com/api"

class DetailedAnalyzer:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
    
    def setup_12_players_scenario(self):
        """Setup the 12 players, 6 courts scenario for detailed analysis"""
        print("=== Setting up 12 Players, 6 Courts Scenario ===")
        
        # Initialize and reset
        self.session.post(f"{self.base_url}/init")
        self.session.post(f"{self.base_url}/session/reset")
        
        # Clear existing players
        players_response = self.session.get(f"{self.base_url}/players")
        if players_response.status_code == 200:
            players = players_response.json()
            for player in players:
                self.session.delete(f"{self.base_url}/players/{player['id']}")
        
        # Create exactly 12 players (4 per category)
        players_config = [
            # Beginner category (4 players)
            {"name": "Alex Johnson", "category": "Beginner"},
            {"name": "Sarah Wilson", "category": "Beginner"},
            {"name": "Mike Davis", "category": "Beginner"},
            {"name": "Lisa Brown", "category": "Beginner"},
            
            # Intermediate category (4 players)
            {"name": "David Chen", "category": "Intermediate"},
            {"name": "Emma Rodriguez", "category": "Intermediate"},
            {"name": "James Kim", "category": "Intermediate"},
            {"name": "Rachel Martinez", "category": "Intermediate"},
            
            # Advanced category (4 players)
            {"name": "Jennifer Walsh", "category": "Advanced"},
            {"name": "Robert Thompson", "category": "Advanced"},
            {"name": "Maria Garcia", "category": "Advanced"},
            {"name": "Steven Lee", "category": "Advanced"}
        ]
        
        created_players = []
        for config in players_config:
            response = self.session.post(f"{self.base_url}/players", json=config)
            if response.status_code == 200:
                created_players.append(response.json())
        
        print(f"Created {len(created_players)} players")
        
        # Configure session
        config = {
            "numCourts": 6,
            "playSeconds": 720,
            "bufferSeconds": 30,
            "allowSingles": True,
            "allowDoubles": True,
            "allowCrossCategory": False
        }
        
        response = self.session.put(f"{self.base_url}/session/config", json=config)
        print(f"Configured session with 6 courts")
        
        return created_players
    
    def analyze_algorithm_behavior(self):
        """Analyze how the algorithm behaves with 12 players"""
        print("\n=== Algorithm Analysis ===")
        
        # Start session
        start_response = self.session.post(f"{self.base_url}/session/start")
        if start_response.status_code != 200:
            print(f"Failed to start session: {start_response.text}")
            return
        
        start_data = start_response.json()
        print(f"Session started: {start_data}")
        
        # Get matches
        matches_response = self.session.get(f"{self.base_url}/matches")
        if matches_response.status_code != 200:
            print(f"Failed to get matches: {matches_response.text}")
            return
        
        matches = matches_response.json()
        print(f"\nTotal matches created: {len(matches)}")
        
        # Analyze by category
        category_analysis = {}
        for match in matches:
            cat = match["category"]
            match_type = match["matchType"]
            court = match["courtIndex"]
            
            if cat not in category_analysis:
                category_analysis[cat] = {"matches": [], "courts": set(), "players": set()}
            
            category_analysis[cat]["matches"].append({
                "type": match_type,
                "court": court,
                "teamA": match["teamA"],
                "teamB": match["teamB"]
            })
            category_analysis[cat]["courts"].add(court)
            category_analysis[cat]["players"].update(match["teamA"] + match["teamB"])
        
        print("\n=== Category Analysis ===")
        total_courts_used = set()
        for cat, data in category_analysis.items():
            matches_count = len(data["matches"])
            courts_used = len(data["courts"])
            players_used = len(data["players"])
            
            print(f"\n{cat} Category:")
            print(f"  - Matches: {matches_count}")
            print(f"  - Courts used: {courts_used} (indices: {sorted(data['courts'])})")
            print(f"  - Players involved: {players_used}")
            
            for i, match in enumerate(data["matches"]):
                print(f"    Match {i+1}: {match['type']} on Court {match['court']} "
                      f"(Team A: {len(match['teamA'])}, Team B: {len(match['teamB'])})")
            
            total_courts_used.update(data["courts"])
        
        print(f"\n=== Overall Court Utilization ===")
        print(f"Total unique courts used: {len(total_courts_used)} out of 6 available")
        print(f"Court indices used: {sorted(total_courts_used)}")
        print(f"Utilization rate: {len(total_courts_used)/6*100:.1f}%")
        
        # Theoretical optimal analysis
        print(f"\n=== Theoretical Optimal Analysis ===")
        print(f"With 12 players and doubles priority:")
        print(f"  - Each category has 4 players")
        print(f"  - Each category can create 1 doubles match (4 players)")
        print(f"  - Total: 3 doubles matches = 3 courts used")
        print(f"  - Remaining capacity: 3 courts unused")
        print(f"  - Could potentially create more matches if algorithm was different")
        
        # Check if we could create more matches
        print(f"\n=== Potential Improvements ===")
        print(f"Current algorithm creates 1 match per category (fair distribution)")
        print(f"Alternative: Could create multiple matches per category if players allow")
        print(f"For example: Beginner category (4 players) could create:")
        print(f"  - 1 doubles match (4 players) OR")
        print(f"  - 2 singles matches (4 players)")
        print(f"This would use more courts but might not be 'fair' across categories")
        
        return category_analysis
    
    def test_cross_category_improvement(self):
        """Test if cross-category matching improves court utilization"""
        print(f"\n=== Testing Cross-Category Improvement ===")
        
        # Reset and configure with cross-category
        self.session.post(f"{self.base_url}/session/reset")
        
        config = {
            "numCourts": 6,
            "playSeconds": 720,
            "bufferSeconds": 30,
            "allowSingles": True,
            "allowDoubles": True,
            "allowCrossCategory": True  # Enable cross-category
        }
        
        response = self.session.put(f"{self.base_url}/session/config", json=config)
        print(f"Enabled cross-category matching")
        
        # Start session
        start_response = self.session.post(f"{self.base_url}/session/start")
        if start_response.status_code != 200:
            print(f"Failed to start session: {start_response.text}")
            return
        
        # Get matches
        matches_response = self.session.get(f"{self.base_url}/matches")
        matches = matches_response.json()
        
        courts_used = len(set(match["courtIndex"] for match in matches))
        print(f"Cross-category result: {len(matches)} matches using {courts_used} courts")
        
        # Analyze match types
        match_types = {}
        for match in matches:
            match_type = match["matchType"]
            match_types[match_type] = match_types.get(match_type, 0) + 1
        
        print(f"Match types: {match_types}")
        
        if courts_used > 3:
            print(f"✅ Cross-category matching improved court utilization!")
        else:
            print(f"❌ Cross-category matching did not improve court utilization")
    
    def run_analysis(self):
        """Run complete analysis"""
        print("🔍 DETAILED COURT ALLOCATION ALGORITHM ANALYSIS")
        print("=" * 60)
        
        # Setup scenario
        players = self.setup_12_players_scenario()
        
        # Analyze current algorithm
        analysis = self.analyze_algorithm_behavior()
        
        # Test cross-category improvement
        self.test_cross_category_improvement()
        
        print(f"\n" + "=" * 60)
        print("🔍 ANALYSIS COMPLETE")
        print("=" * 60)

if __name__ == "__main__":
    analyzer = DetailedAnalyzer()
    analyzer.run_analysis()