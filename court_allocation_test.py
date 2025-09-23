#!/usr/bin/env python3
"""
Court Allocation Optimization Tests for Pickleball Session Manager
Tests specific scenarios for court utilization efficiency
"""

import requests
import json
import os
from typing import Dict, List, Any
import time

# Get backend URL from environment
BACKEND_URL = "https://match-scheduler-11.preview.emergentagent.com/api"

class CourtAllocationTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "success": success,
            "details": details
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        print()

    def setup_test_environment(self):
        """Initialize the test environment"""
        print("=== Setting Up Test Environment ===")
        
        try:
            # Initialize default categories
            init_response = self.session.post(f"{self.base_url}/init")
            if init_response.status_code == 200:
                self.log_test("Initialize Environment", True, "Default categories and session initialized")
            else:
                self.log_test("Initialize Environment", False, f"Failed to initialize: {init_response.text}")
                return False
                
            # Reset session to clean state
            reset_response = self.session.post(f"{self.base_url}/session/reset")
            if reset_response.status_code == 200:
                self.log_test("Reset Session", True, "Session reset to clean state")
            else:
                self.log_test("Reset Session", False, f"Failed to reset: {reset_response.text}")
                return False
                
            return True
            
        except Exception as e:
            self.log_test("Setup Environment", False, f"Exception: {str(e)}")
            return False

    def clear_existing_players(self):
        """Clear all existing players"""
        try:
            # Get all players
            players_response = self.session.get(f"{self.base_url}/players")
            if players_response.status_code == 200:
                players = players_response.json()
                
                # Delete each player
                for player in players:
                    delete_response = self.session.delete(f"{self.base_url}/players/{player['id']}")
                    if delete_response.status_code != 200:
                        self.log_test("Clear Players", False, f"Failed to delete player {player['name']}")
                        return False
                        
                self.log_test("Clear Existing Players", True, f"Cleared {len(players)} existing players")
                return True
            else:
                self.log_test("Clear Players", False, f"Failed to get players: {players_response.text}")
                return False
                
        except Exception as e:
            self.log_test("Clear Players", False, f"Exception: {str(e)}")
            return False

    def create_test_players(self, player_configs: List[Dict]):
        """Create specific test players"""
        created_players = []
        
        for i, config in enumerate(player_configs):
            try:
                response = self.session.post(f"{self.base_url}/players", json=config)
                if response.status_code == 200:
                    player = response.json()
                    created_players.append(player)
                else:
                    self.log_test(f"Create Player {config['name']}", False, f"Failed: {response.text}")
                    return []
                    
            except Exception as e:
                self.log_test(f"Create Player {config['name']}", False, f"Exception: {str(e)}")
                return []
        
        self.log_test("Create Test Players", True, f"Created {len(created_players)} players")
        return created_players

    def configure_session(self, num_courts: int, allow_singles: bool = True, allow_doubles: bool = True):
        """Configure session with specific court count and format settings"""
        config = {
            "numCourts": num_courts,
            "playSeconds": 720,  # 12 minutes
            "bufferSeconds": 30,
            "allowSingles": allow_singles,
            "allowDoubles": allow_doubles,
            "allowCrossCategory": False  # Test category-based first
        }
        
        try:
            response = self.session.put(f"{self.base_url}/session/config", json=config)
            if response.status_code == 200:
                self.log_test("Configure Session", True, f"Set {num_courts} courts, singles={allow_singles}, doubles={allow_doubles}")
                return True
            else:
                self.log_test("Configure Session", False, f"Failed: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Configure Session", False, f"Exception: {str(e)}")
            return False

    def start_session_and_analyze(self, expected_min_courts: int, scenario_name: str):
        """Start session and analyze court utilization"""
        try:
            # Start the session
            start_response = self.session.post(f"{self.base_url}/session/start")
            if start_response.status_code != 200:
                self.log_test(f"{scenario_name} - Session Start", False, f"Failed to start: {start_response.text}")
                return False
                
            start_data = start_response.json()
            matches_created = start_data.get("matches_created", 0)
            
            # Get all matches
            matches_response = self.session.get(f"{self.base_url}/matches")
            if matches_response.status_code != 200:
                self.log_test(f"{scenario_name} - Get Matches", False, f"Failed to get matches: {matches_response.text}")
                return False
                
            matches = matches_response.json()
            
            # Analyze court utilization
            court_indices = [match["courtIndex"] for match in matches]
            unique_courts_used = len(set(court_indices))
            total_matches = len(matches)
            
            # Calculate utilization percentage
            session_response = self.session.get(f"{self.base_url}/session")
            if session_response.status_code == 200:
                session = session_response.json()
                total_courts_available = session["config"]["numCourts"]
                utilization_percentage = (unique_courts_used / total_courts_available) * 100 if total_courts_available > 0 else 0
            else:
                total_courts_available = 0
                utilization_percentage = 0
            
            # Analyze matches by category and type
            matches_by_category = {}
            matches_by_type = {"singles": 0, "doubles": 0}
            
            for match in matches:
                category = match["category"]
                match_type = match["matchType"]
                
                if category not in matches_by_category:
                    matches_by_category[category] = {"singles": 0, "doubles": 0}
                matches_by_category[category][match_type] += 1
                matches_by_type[match_type] += 1
            
            # Log detailed analysis
            analysis_details = (
                f"Courts Used: {unique_courts_used}/{total_courts_available} ({utilization_percentage:.1f}%), "
                f"Total Matches: {total_matches}, "
                f"Court Indices: {sorted(set(court_indices))}, "
                f"Matches by Type: {matches_by_type}, "
                f"Matches by Category: {matches_by_category}"
            )
            
            # Check if meets minimum court requirement
            if unique_courts_used >= expected_min_courts:
                self.log_test(f"{scenario_name} - Court Utilization", True, analysis_details)
                success = True
            else:
                self.log_test(f"{scenario_name} - Court Utilization", False, 
                            f"Only {unique_courts_used} courts used, expected at least {expected_min_courts}. {analysis_details}")
                success = False
            
            # Additional analysis for unused courts
            if unique_courts_used < total_courts_available:
                unused_courts = total_courts_available - unique_courts_used
                self.log_test(f"{scenario_name} - Unused Courts Analysis", True, 
                            f"{unused_courts} courts left unused - analyzing if this is optimal")
            
            return success
            
        except Exception as e:
            self.log_test(f"{scenario_name} - Analysis", False, f"Exception: {str(e)}")
            return False

    def test_10_players_5_courts(self):
        """Test Scenario 1: 10 players, 5 courts - should use more than 2 courts"""
        print("=== Testing Scenario 1: 10 Players, 5 Courts ===")
        
        if not self.setup_test_environment():
            return False
            
        if not self.clear_existing_players():
            return False
        
        # Create exactly 10 players distributed across categories
        players_config = [
            # Beginner category (4 players)
            {"name": "Alex Johnson", "category": "Beginner"},
            {"name": "Sarah Wilson", "category": "Beginner"},
            {"name": "Mike Davis", "category": "Beginner"},
            {"name": "Lisa Brown", "category": "Beginner"},
            
            # Intermediate category (3 players)
            {"name": "David Chen", "category": "Intermediate"},
            {"name": "Emma Rodriguez", "category": "Intermediate"},
            {"name": "James Kim", "category": "Intermediate"},
            
            # Advanced category (3 players)
            {"name": "Jennifer Walsh", "category": "Advanced"},
            {"name": "Robert Thompson", "category": "Advanced"},
            {"name": "Maria Garcia", "category": "Advanced"}
        ]
        
        created_players = self.create_test_players(players_config)
        if len(created_players) != 10:
            return False
        
        # Configure session with 5 courts, both singles and doubles enabled
        if not self.configure_session(num_courts=5, allow_singles=True, allow_doubles=True):
            return False
        
        # Start session and analyze - expect more than 2 courts (ideally 3-5)
        return self.start_session_and_analyze(expected_min_courts=3, scenario_name="10 Players, 5 Courts")

    def test_12_players_6_courts(self):
        """Test Scenario 2: 12 players, 6 courts - should use most/all courts efficiently"""
        print("=== Testing Scenario 2: 12 Players, 6 Courts ===")
        
        if not self.setup_test_environment():
            return False
            
        if not self.clear_existing_players():
            return False
        
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
        
        created_players = self.create_test_players(players_config)
        if len(created_players) != 12:
            return False
        
        # Configure session with 6 courts, both formats enabled
        if not self.configure_session(num_courts=6, allow_singles=True, allow_doubles=True):
            return False
        
        # Start session and analyze - expect most courts used (4-6 courts)
        return self.start_session_and_analyze(expected_min_courts=4, scenario_name="12 Players, 6 Courts")

    def test_8_players_4_courts(self):
        """Test Scenario 3: 8 players, 4 courts - should use all 4 courts or close to it"""
        print("=== Testing Scenario 3: 8 Players, 4 Courts ===")
        
        if not self.setup_test_environment():
            return False
            
        if not self.clear_existing_players():
            return False
        
        # Create exactly 8 players
        players_config = [
            # Beginner category (3 players)
            {"name": "Alex Johnson", "category": "Beginner"},
            {"name": "Sarah Wilson", "category": "Beginner"},
            {"name": "Mike Davis", "category": "Beginner"},
            
            # Intermediate category (3 players)
            {"name": "David Chen", "category": "Intermediate"},
            {"name": "Emma Rodriguez", "category": "Intermediate"},
            {"name": "James Kim", "category": "Intermediate"},
            
            # Advanced category (2 players)
            {"name": "Jennifer Walsh", "category": "Advanced"},
            {"name": "Robert Thompson", "category": "Advanced"}
        ]
        
        created_players = self.create_test_players(players_config)
        if len(created_players) != 8:
            return False
        
        # Configure session with 4 courts
        if not self.configure_session(num_courts=4, allow_singles=True, allow_doubles=True):
            return False
        
        # Start session and analyze - expect all or most courts used (3-4 courts)
        return self.start_session_and_analyze(expected_min_courts=3, scenario_name="8 Players, 4 Courts")

    def test_cross_category_optimization(self):
        """Test court optimization with cross-category matching enabled"""
        print("=== Testing Cross-Category Court Optimization ===")
        
        if not self.setup_test_environment():
            return False
            
        if not self.clear_existing_players():
            return False
        
        # Create 10 players with uneven distribution
        players_config = [
            # Beginner category (5 players)
            {"name": "Alex Johnson", "category": "Beginner"},
            {"name": "Sarah Wilson", "category": "Beginner"},
            {"name": "Mike Davis", "category": "Beginner"},
            {"name": "Lisa Brown", "category": "Beginner"},
            {"name": "Tom Anderson", "category": "Beginner"},
            
            # Intermediate category (1 player)
            {"name": "David Chen", "category": "Intermediate"},
            
            # Advanced category (4 players)
            {"name": "Jennifer Walsh", "category": "Advanced"},
            {"name": "Robert Thompson", "category": "Advanced"},
            {"name": "Maria Garcia", "category": "Advanced"},
            {"name": "Steven Lee", "category": "Advanced"}
        ]
        
        created_players = self.create_test_players(players_config)
        if len(created_players) != 10:
            return False
        
        # Configure session with cross-category enabled
        config = {
            "numCourts": 5,
            "playSeconds": 720,
            "bufferSeconds": 30,
            "allowSingles": True,
            "allowDoubles": True,
            "allowCrossCategory": True  # Enable cross-category matching
        }
        
        try:
            response = self.session.put(f"{self.base_url}/session/config", json=config)
            if response.status_code == 200:
                self.log_test("Configure Cross-Category", True, "Cross-category matching enabled")
            else:
                self.log_test("Configure Cross-Category", False, f"Failed: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Configure Cross-Category", False, f"Exception: {str(e)}")
            return False
        
        # Start session and analyze
        return self.start_session_and_analyze(expected_min_courts=3, scenario_name="Cross-Category 10 Players, 5 Courts")

    def test_doubles_only_optimization(self):
        """Test court optimization with doubles-only format"""
        print("=== Testing Doubles-Only Court Optimization ===")
        
        if not self.setup_test_environment():
            return False
            
        if not self.clear_existing_players():
            return False
        
        # Create 12 players (perfect for doubles)
        players_config = [
            {"name": f"Player {i+1}", "category": ["Beginner", "Intermediate", "Advanced"][i % 3]}
            for i in range(12)
        ]
        
        created_players = self.create_test_players(players_config)
        if len(created_players) != 12:
            return False
        
        # Configure session with doubles only
        if not self.configure_session(num_courts=6, allow_singles=False, allow_doubles=True):
            return False
        
        # Start session and analyze - should create 3 doubles matches (6 courts available, 12 players = 3 matches)
        return self.start_session_and_analyze(expected_min_courts=3, scenario_name="Doubles-Only 12 Players, 6 Courts")

    def test_singles_only_optimization(self):
        """Test court optimization with singles-only format"""
        print("=== Testing Singles-Only Court Optimization ===")
        
        if not self.setup_test_environment():
            return False
            
        if not self.clear_existing_players():
            return False
        
        # Create 8 players (perfect for singles)
        players_config = [
            {"name": f"Player {i+1}", "category": ["Beginner", "Intermediate", "Advanced"][i % 3]}
            for i in range(8)
        ]
        
        created_players = self.create_test_players(players_config)
        if len(created_players) != 8:
            return False
        
        # Configure session with singles only
        if not self.configure_session(num_courts=4, allow_singles=True, allow_doubles=False):
            return False
        
        # Start session and analyze - should create 4 singles matches
        return self.start_session_and_analyze(expected_min_courts=4, scenario_name="Singles-Only 8 Players, 4 Courts")

    def run_all_tests(self):
        """Run all court allocation optimization tests"""
        print("🏓 COURT ALLOCATION OPTIMIZATION TESTING")
        print("=" * 60)
        
        test_methods = [
            self.test_10_players_5_courts,
            self.test_12_players_6_courts,
            self.test_8_players_4_courts,
            self.test_cross_category_optimization,
            self.test_doubles_only_optimization,
            self.test_singles_only_optimization
        ]
        
        passed_tests = 0
        total_tests = len(test_methods)
        
        for test_method in test_methods:
            try:
                if test_method():
                    passed_tests += 1
            except Exception as e:
                print(f"❌ EXCEPTION in {test_method.__name__}: {str(e)}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("🏓 COURT ALLOCATION OPTIMIZATION TEST SUMMARY")
        print("=" * 60)
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        for result in self.test_results:
            print(f"{result['status']}: {result['test']}")
            if result['details']:
                print(f"   {result['details']}")
        
        print(f"\n📊 OVERALL RESULTS: {passed_tests}/{total_tests} scenarios passed ({success_rate:.1f}%)")
        
        if success_rate >= 80:
            print("✅ COURT ALLOCATION OPTIMIZATION: EXCELLENT")
        elif success_rate >= 60:
            print("⚠️  COURT ALLOCATION OPTIMIZATION: GOOD - Some improvements needed")
        else:
            print("❌ COURT ALLOCATION OPTIMIZATION: NEEDS IMPROVEMENT")
        
        return success_rate >= 80

if __name__ == "__main__":
    tester = CourtAllocationTester()
    tester.run_all_tests()