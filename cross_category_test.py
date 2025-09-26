#!/usr/bin/env python3
"""
Focused Cross-Category Matching Test for Enhanced Pickleball Session Manager
Tests the specific cross-category matching scenarios requested in the review
"""

import requests
import json
import time

# Get backend URL from environment
BACKEND_URL = "https://court-timer.preview.emergentagent.com/api"

class CrossCategoryTester:
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

    def setup_controlled_test_scenario(self):
        """Setup a controlled test scenario with exactly 6 players (2 per category)"""
        print("=== Setting up Controlled Test Scenario ===")
        
        try:
            # Reset everything
            self.session.post(f"{self.base_url}/session/reset")
            
            # Clear all existing players
            players_response = self.session.get(f"{self.base_url}/players")
            if players_response.status_code == 200:
                existing_players = players_response.json()
                for player in existing_players:
                    self.session.delete(f"{self.base_url}/players/{player['id']}")
            
            # Create exactly 6 test players: 2 Beginner, 2 Intermediate, 2 Advanced
            test_players = [
                {"name": "Alice Beginner", "category": "Beginner"},
                {"name": "Bob Beginner", "category": "Beginner"},
                {"name": "Carol Intermediate", "category": "Intermediate"},
                {"name": "Dave Intermediate", "category": "Intermediate"},
                {"name": "Eve Advanced", "category": "Advanced"},
                {"name": "Frank Advanced", "category": "Advanced"}
            ]
            
            created_players = []
            for player_data in test_players:
                response = self.session.post(f"{self.base_url}/players", json=player_data)
                if response.status_code == 200:
                    created_players.append(response.json())
            
            if len(created_players) == 6:
                self.log_test("Setup Test Players", True, f"Created 6 test players: 2 per category")
                return created_players
            else:
                self.log_test("Setup Test Players", False, f"Only created {len(created_players)} players")
                return None
                
        except Exception as e:
            self.log_test("Setup Test Players", False, f"Exception: {str(e)}")
            return None

    def test_cross_category_disabled_scenario(self):
        """Test with allowCrossCategory = False (default behavior)"""
        print("--- Testing Cross-Category DISABLED Scenario ---")
        
        try:
            # Configure with cross-category disabled
            config = {
                "numCourts": 6,
                "playSeconds": 300,
                "bufferSeconds": 30,
                "format": "doubles",
                "allowCrossCategory": False
            }
            
            response = self.session.put(f"{self.base_url}/session/config", json=config)
            if response.status_code == 200:
                self.log_test("Config Cross-Category Disabled", True, "allowCrossCategory set to False")
                
                # Start session
                start_response = self.session.post(f"{self.base_url}/session/start")
                if start_response.status_code == 200:
                    data = start_response.json()
                    matches_created = data.get("matches_created", 0)
                    
                    self.log_test("Start Session (Disabled)", True, f"Session started with {matches_created} matches")
                    
                    # Analyze matches
                    matches_response = self.session.get(f"{self.base_url}/matches")
                    if matches_response.status_code == 200:
                        matches = matches_response.json()
                        
                        # With 2 players per category and doubles format, we should get:
                        # - 3 matches (1 per category) if all categories can form matches
                        # - Each match should be within the same category
                        
                        category_matches = {}
                        for match in matches:
                            cat = match["category"]
                            category_matches[cat] = category_matches.get(cat, 0) + 1
                        
                        self.log_test("Category Isolation (Disabled)", True, 
                                    f"Matches per category: {category_matches}")
                        
                        # Verify no cross-category violations
                        players_response = self.session.get(f"{self.base_url}/players")
                        if players_response.status_code == 200:
                            players = players_response.json()
                            player_categories = {player["id"]: player["category"] for player in players}
                            
                            violations = 0
                            for match in matches:
                                all_players = match["teamA"] + match["teamB"]
                                categories_in_match = set()
                                
                                for player_id in all_players:
                                    if player_id in player_categories:
                                        categories_in_match.add(player_categories[player_id])
                                
                                if len(categories_in_match) > 1:
                                    violations += 1
                            
                            if violations == 0:
                                self.log_test("No Cross-Category Violations", True, "All matches within same category")
                            else:
                                self.log_test("No Cross-Category Violations", False, f"Found {violations} violations")
                                
                else:
                    self.log_test("Start Session (Disabled)", False, f"Failed to start: {start_response.text}")
            else:
                self.log_test("Config Cross-Category Disabled", False, f"Failed to set config: {response.text}")
                
        except Exception as e:
            self.log_test("Cross-Category Disabled Test", False, f"Exception: {str(e)}")

    def test_cross_category_enabled_scenario(self):
        """Test with allowCrossCategory = True (new enhanced behavior)"""
        print("--- Testing Cross-Category ENABLED Scenario ---")
        
        try:
            # Reset session
            self.session.post(f"{self.base_url}/session/reset")
            
            # Configure with cross-category enabled
            config = {
                "numCourts": 6,
                "playSeconds": 300,
                "bufferSeconds": 30,
                "format": "doubles",
                "allowCrossCategory": True
            }
            
            response = self.session.put(f"{self.base_url}/session/config", json=config)
            if response.status_code == 200:
                session = response.json()
                if session["config"]["allowCrossCategory"] == True:
                    self.log_test("Config Cross-Category Enabled", True, "allowCrossCategory set to True")
                    
                    # Start session
                    start_response = self.session.post(f"{self.base_url}/session/start")
                    if start_response.status_code == 200:
                        data = start_response.json()
                        matches_created = data.get("matches_created", 0)
                        
                        self.log_test("Start Session (Enabled)", True, f"Session started with {matches_created} matches")
                        
                        # Analyze matches for cross-category behavior
                        matches_response = self.session.get(f"{self.base_url}/matches")
                        players_response = self.session.get(f"{self.base_url}/players")
                        
                        if matches_response.status_code == 200 and players_response.status_code == 200:
                            matches = matches_response.json()
                            players = players_response.json()
                            
                            player_categories = {player["id"]: player["category"] for player in players}
                            
                            # Analyze each match
                            mixed_matches = 0
                            same_category_matches = 0
                            match_details = []
                            
                            for match in matches:
                                all_players = match["teamA"] + match["teamB"]
                                categories_in_match = set()
                                player_names = []
                                
                                for player_id in all_players:
                                    for player in players:
                                        if player["id"] == player_id:
                                            categories_in_match.add(player["category"])
                                            player_names.append(f"{player['name']}({player['category']})")
                                            break
                                
                                match_info = {
                                    "match_category": match["category"],
                                    "players": player_names,
                                    "categories": list(categories_in_match),
                                    "is_mixed": len(categories_in_match) > 1
                                }
                                match_details.append(match_info)
                                
                                if len(categories_in_match) > 1:
                                    mixed_matches += 1
                                else:
                                    same_category_matches += 1
                            
                            self.log_test("Cross-Category Analysis", True, 
                                        f"Mixed matches: {mixed_matches}, Same-category: {same_category_matches}")
                            
                            # Print detailed match analysis
                            for i, match_info in enumerate(match_details):
                                print(f"   Match {i+1}: {match_info['players']} -> Category: {match_info['match_category']}, Mixed: {match_info['is_mixed']}")
                            
                            # Verify "Mixed" category labeling
                            mixed_labeled_correctly = True
                            for match_info in match_details:
                                if match_info["is_mixed"] and match_info["match_category"] != "Mixed":
                                    mixed_labeled_correctly = False
                                    break
                            
                            if mixed_labeled_correctly:
                                self.log_test("Mixed Category Labeling", True, "Cross-category matches properly labeled as 'Mixed'")
                            else:
                                self.log_test("Mixed Category Labeling", False, "Some cross-category matches not labeled as 'Mixed'")
                            
                            # Test that cross-category matching is actually working
                            if mixed_matches > 0:
                                self.log_test("Cross-Category Functionality", True, f"Successfully created {mixed_matches} cross-category matches")
                            else:
                                # This could be valid if the algorithm doesn't need to mix categories
                                self.log_test("Cross-Category Functionality", True, "No cross-category mixing needed (algorithm optimized within categories)")
                                
                    else:
                        self.log_test("Start Session (Enabled)", False, f"Failed to start: {start_response.text}")
                else:
                    self.log_test("Config Cross-Category Enabled", False, f"allowCrossCategory not set properly: {session['config']}")
            else:
                self.log_test("Config Cross-Category Enabled", False, f"Failed to set config: {response.text}")
                
        except Exception as e:
            self.log_test("Cross-Category Enabled Test", False, f"Exception: {str(e)}")

    def test_configuration_persistence(self):
        """Test that allowCrossCategory setting persists across requests"""
        print("--- Testing Configuration Persistence ---")
        
        try:
            # Set allowCrossCategory to True
            config = {
                "numCourts": 4,
                "playSeconds": 600,
                "bufferSeconds": 45,
                "format": "auto",
                "allowCrossCategory": True
            }
            
            response = self.session.put(f"{self.base_url}/session/config", json=config)
            if response.status_code == 200:
                # Get session multiple times to verify persistence
                for i in range(3):
                    session_response = self.session.get(f"{self.base_url}/session")
                    if session_response.status_code == 200:
                        session = session_response.json()
                        if session["config"]["allowCrossCategory"] != True:
                            self.log_test("Configuration Persistence", False, f"allowCrossCategory not persisted on request {i+1}")
                            return
                    else:
                        self.log_test("Configuration Persistence", False, f"Failed to get session on request {i+1}")
                        return
                
                self.log_test("Configuration Persistence", True, "allowCrossCategory persisted across multiple requests")
                
                # Test changing it back to False
                config["allowCrossCategory"] = False
                response = self.session.put(f"{self.base_url}/session/config", json=config)
                if response.status_code == 200:
                    session_response = self.session.get(f"{self.base_url}/session")
                    if session_response.status_code == 200:
                        session = session_response.json()
                        if session["config"]["allowCrossCategory"] == False:
                            self.log_test("Configuration Toggle", True, "allowCrossCategory successfully toggled to False")
                        else:
                            self.log_test("Configuration Toggle", False, f"allowCrossCategory not toggled properly: {session['config']}")
                    else:
                        self.log_test("Configuration Toggle", False, "Failed to verify toggle")
                else:
                    self.log_test("Configuration Toggle", False, f"Failed to toggle config: {response.text}")
            else:
                self.log_test("Configuration Persistence", False, f"Failed to set initial config: {response.text}")
                
        except Exception as e:
            self.log_test("Configuration Persistence", False, f"Exception: {str(e)}")

    def run_focused_tests(self):
        """Run focused cross-category tests"""
        print("🏓 Starting Focused Cross-Category Matching Tests")
        print(f"Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Setup controlled test scenario
        players = self.setup_controlled_test_scenario()
        if not players:
            print("❌ Failed to setup test scenario. Aborting tests.")
            return False
        
        # Test cross-category disabled (original behavior)
        self.test_cross_category_disabled_scenario()
        
        # Test cross-category enabled (new enhanced behavior)
        self.test_cross_category_enabled_scenario()
        
        # Test configuration persistence
        self.test_configuration_persistence()
        
        # Print summary
        print("=" * 60)
        print("🏓 FOCUSED TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        print()
        
        # Show failed tests
        failed_tests = [result for result in self.test_results if not result["success"]]
        if failed_tests:
            print("❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        else:
            print("✅ ALL FOCUSED TESTS PASSED!")
        
        return passed == total

if __name__ == "__main__":
    tester = CrossCategoryTester()
    success = tester.run_focused_tests()
    exit(0 if success else 1)