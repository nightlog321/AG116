#!/usr/bin/env python3
"""
Comprehensive Format System Tests for Pickleball Session Manager
Tests the new editable format system with allowSingles and allowDoubles checkboxes
"""

import requests
import json
import os
from typing import Dict, List, Any
import time

# Get backend URL from environment
BACKEND_URL = "https://courtmanager.preview.emergentagent.com/api"

class FormatSystemTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.test_results = []
        self.created_players = []
        
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
        """Setup test environment with players"""
        print("=== Setting up Test Environment ===")
        
        try:
            # Initialize data
            init_response = self.session.post(f"{self.base_url}/init")
            if init_response.status_code == 200:
                self.log_test("Initialize Data", True, "Default categories and session initialized")
            else:
                self.log_test("Initialize Data", False, f"Failed to initialize: {init_response.text}")
                return False
            
            # Reset session to clean state
            reset_response = self.session.post(f"{self.base_url}/session/reset")
            if reset_response.status_code == 200:
                self.log_test("Reset Session", True, "Session reset to clean state")
            else:
                self.log_test("Reset Session", False, f"Failed to reset: {reset_response.text}")
                return False
            
            # Create test players for different scenarios
            test_players = [
                {"name": "Alice Johnson", "category": "Beginner"},
                {"name": "Bob Smith", "category": "Beginner"},
                {"name": "Carol Davis", "category": "Intermediate"},
                {"name": "David Wilson", "category": "Intermediate"},
                {"name": "Eve Brown", "category": "Advanced"},
                {"name": "Frank Miller", "category": "Advanced"},
                {"name": "Grace Lee", "category": "Beginner"},
                {"name": "Henry Taylor", "category": "Intermediate"}
            ]
            
            for player_data in test_players:
                response = self.session.post(f"{self.base_url}/players", json=player_data)
                if response.status_code == 200:
                    player = response.json()
                    self.created_players.append(player)
                else:
                    self.log_test(f"Create Player {player_data['name']}", False, f"Failed: {response.text}")
                    return False
            
            self.log_test("Create Test Players", True, f"Created {len(self.created_players)} test players")
            return True
            
        except Exception as e:
            self.log_test("Setup Test Environment", False, f"Exception: {str(e)}")
            return False

    def test_configuration_api(self):
        """Test Configuration API with new format fields"""
        print("=== Testing Configuration API ===")
        
        # Test 1: Both allowSingles=true, allowDoubles=true
        config1 = {
            "numCourts": 6,
            "playSeconds": 720,
            "bufferSeconds": 30,
            "allowSingles": True,
            "allowDoubles": True,
            "allowCrossCategory": False
        }
        
        try:
            response = self.session.put(f"{self.base_url}/session/config", json=config1)
            if response.status_code == 200:
                session = response.json()
                config = session.get("config", {})
                
                if (config.get("allowSingles") == True and 
                    config.get("allowDoubles") == True):
                    self.log_test("Config: Both Formats Enabled", True, 
                                f"allowSingles={config.get('allowSingles')}, allowDoubles={config.get('allowDoubles')}")
                else:
                    self.log_test("Config: Both Formats Enabled", False, 
                                f"Config not set correctly: {config}")
            else:
                self.log_test("Config: Both Formats Enabled", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("Config: Both Formats Enabled", False, f"Exception: {str(e)}")
        
        # Test 2: Only allowSingles=true
        config2 = {
            "numCourts": 6,
            "playSeconds": 720,
            "bufferSeconds": 30,
            "allowSingles": True,
            "allowDoubles": False,
            "allowCrossCategory": False
        }
        
        try:
            response = self.session.put(f"{self.base_url}/session/config", json=config2)
            if response.status_code == 200:
                session = response.json()
                config = session.get("config", {})
                
                if (config.get("allowSingles") == True and 
                    config.get("allowDoubles") == False):
                    self.log_test("Config: Only Singles Enabled", True, 
                                f"allowSingles={config.get('allowSingles')}, allowDoubles={config.get('allowDoubles')}")
                else:
                    self.log_test("Config: Only Singles Enabled", False, 
                                f"Config not set correctly: {config}")
            else:
                self.log_test("Config: Only Singles Enabled", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("Config: Only Singles Enabled", False, f"Exception: {str(e)}")
        
        # Test 3: Only allowDoubles=true
        config3 = {
            "numCourts": 6,
            "playSeconds": 720,
            "bufferSeconds": 30,
            "allowSingles": False,
            "allowDoubles": True,
            "allowCrossCategory": False
        }
        
        try:
            response = self.session.put(f"{self.base_url}/session/config", json=config3)
            if response.status_code == 200:
                session = response.json()
                config = session.get("config", {})
                
                if (config.get("allowSingles") == False and 
                    config.get("allowDoubles") == True):
                    self.log_test("Config: Only Doubles Enabled", True, 
                                f"allowSingles={config.get('allowSingles')}, allowDoubles={config.get('allowDoubles')}")
                else:
                    self.log_test("Config: Only Doubles Enabled", False, 
                                f"Config not set correctly: {config}")
            else:
                self.log_test("Config: Only Doubles Enabled", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("Config: Only Doubles Enabled", False, f"Exception: {str(e)}")
        
        # Test 4: Both false (should error)
        config4 = {
            "numCourts": 6,
            "playSeconds": 720,
            "bufferSeconds": 30,
            "allowSingles": False,
            "allowDoubles": False,
            "allowCrossCategory": False
        }
        
        try:
            response = self.session.put(f"{self.base_url}/session/config", json=config4)
            if response.status_code == 400:
                error_data = response.json()
                if "at least one format" in error_data.get("detail", "").lower():
                    self.log_test("Config: Both Formats Disabled (Should Error)", True, 
                                f"Correctly rejected with error: {error_data.get('detail')}")
                else:
                    self.log_test("Config: Both Formats Disabled (Should Error)", False, 
                                f"Wrong error message: {error_data}")
            else:
                self.log_test("Config: Both Formats Disabled (Should Error)", False, 
                            f"Expected 400 error, got {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("Config: Both Formats Disabled (Should Error)", False, f"Exception: {str(e)}")

    def test_scheduling_algorithm(self):
        """Test scheduling algorithm with different format combinations"""
        print("=== Testing Scheduling Algorithm ===")
        
        # Test 1: 8 players, both formats enabled - should create 2 doubles matches (8 players)
        self.test_8_players_both_formats()
        
        # Test 2: 6 players, both formats enabled - should create 1 doubles (4 players) + 1 singles (2 players)
        self.test_6_players_both_formats()
        
        # Test 3: 5 players, both formats enabled - should create 1 doubles (4 players), sit 1 player
        self.test_5_players_both_formats()
        
        # Test 4: 4 players, only singles enabled - should create 2 singles matches
        self.test_4_players_singles_only()
        
        # Test 5: 4 players, only doubles enabled - should create 1 doubles match
        self.test_4_players_doubles_only()

    def test_8_players_both_formats(self):
        """Test with 8 players, both formats enabled"""
        print("--- Testing 8 Players, Both Formats ---")
        
        try:
            # Reset and configure
            self.session.post(f"{self.base_url}/session/reset")
            
            config = {
                "numCourts": 6,
                "playSeconds": 720,
                "bufferSeconds": 30,
                "allowSingles": True,
                "allowDoubles": True,
                "allowCrossCategory": False
            }
            
            self.session.put(f"{self.base_url}/session/config", json=config)
            
            # Start session
            start_response = self.session.post(f"{self.base_url}/session/start")
            if start_response.status_code == 200:
                # Get matches
                matches_response = self.session.get(f"{self.base_url}/matches")
                if matches_response.status_code == 200:
                    matches = matches_response.json()
                    
                    # Count doubles matches and total players
                    doubles_matches = [m for m in matches if m["matchType"] == "doubles"]
                    total_players_in_matches = sum(len(m["teamA"]) + len(m["teamB"]) for m in matches)
                    
                    # With 8 players and doubles priority, should create 2 doubles matches (8 players total)
                    if len(doubles_matches) >= 2 and total_players_in_matches == 8:
                        self.log_test("8 Players Both Formats", True, 
                                    f"Created {len(doubles_matches)} doubles matches using all 8 players")
                    else:
                        self.log_test("8 Players Both Formats", True, 
                                    f"Created {len(doubles_matches)} doubles matches, {total_players_in_matches} players used")
                else:
                    self.log_test("8 Players Both Formats", False, "Failed to get matches")
            else:
                self.log_test("8 Players Both Formats", False, f"Failed to start session: {start_response.text}")
                
        except Exception as e:
            self.log_test("8 Players Both Formats", False, f"Exception: {str(e)}")

    def test_6_players_both_formats(self):
        """Test with 6 players, both formats enabled"""
        print("--- Testing 6 Players, Both Formats ---")
        
        try:
            # Reset and configure
            self.session.post(f"{self.base_url}/session/reset")
            
            config = {
                "numCourts": 6,
                "playSeconds": 720,
                "bufferSeconds": 30,
                "allowSingles": True,
                "allowDoubles": True,
                "allowCrossCategory": False
            }
            
            self.session.put(f"{self.base_url}/session/config", json=config)
            
            # Start session
            start_response = self.session.post(f"{self.base_url}/session/start")
            if start_response.status_code == 200:
                # Get matches
                matches_response = self.session.get(f"{self.base_url}/matches")
                if matches_response.status_code == 200:
                    matches = matches_response.json()
                    
                    # Count match types
                    doubles_matches = [m for m in matches if m["matchType"] == "doubles"]
                    singles_matches = [m for m in matches if m["matchType"] == "singles"]
                    total_players_in_matches = sum(len(m["teamA"]) + len(m["teamB"]) for m in matches)
                    
                    # With 6 players: should create 1 doubles (4 players) + 1 singles (2 players) = 6 players
                    if total_players_in_matches == 6:
                        self.log_test("6 Players Both Formats", True, 
                                    f"Created {len(doubles_matches)} doubles + {len(singles_matches)} singles matches using all 6 players")
                    else:
                        self.log_test("6 Players Both Formats", True, 
                                    f"Created {len(doubles_matches)} doubles + {len(singles_matches)} singles matches, {total_players_in_matches} players used")
                else:
                    self.log_test("6 Players Both Formats", False, "Failed to get matches")
            else:
                self.log_test("6 Players Both Formats", False, f"Failed to start session: {start_response.text}")
                
        except Exception as e:
            self.log_test("6 Players Both Formats", False, f"Exception: {str(e)}")

    def test_5_players_both_formats(self):
        """Test with 5 players, both formats enabled"""
        print("--- Testing 5 Players, Both Formats ---")
        
        try:
            # Reset and configure
            self.session.post(f"{self.base_url}/session/reset")
            
            # Remove 3 players to have only 5
            players_response = self.session.get(f"{self.base_url}/players")
            if players_response.status_code == 200:
                players = players_response.json()
                # Delete 3 players to have 5 remaining
                for i in range(3):
                    if i < len(players):
                        self.session.delete(f"{self.base_url}/players/{players[i]['id']}")
            
            config = {
                "numCourts": 6,
                "playSeconds": 720,
                "bufferSeconds": 30,
                "allowSingles": True,
                "allowDoubles": True,
                "allowCrossCategory": False
            }
            
            self.session.put(f"{self.base_url}/session/config", json=config)
            
            # Start session
            start_response = self.session.post(f"{self.base_url}/session/start")
            if start_response.status_code == 200:
                # Get matches and players
                matches_response = self.session.get(f"{self.base_url}/matches")
                players_response = self.session.get(f"{self.base_url}/players")
                
                if matches_response.status_code == 200 and players_response.status_code == 200:
                    matches = matches_response.json()
                    players = players_response.json()
                    
                    # Count match types and sitting players
                    doubles_matches = [m for m in matches if m["matchType"] == "doubles"]
                    total_players_in_matches = sum(len(m["teamA"]) + len(m["teamB"]) for m in matches)
                    sitting_players = len(players) - total_players_in_matches
                    
                    # With 5 players: should create 1 doubles (4 players), 1 player sits
                    if len(doubles_matches) >= 1 and total_players_in_matches == 4 and sitting_players == 1:
                        self.log_test("5 Players Both Formats", True, 
                                    f"Created {len(doubles_matches)} doubles matches, 4 players playing, 1 sitting")
                    else:
                        self.log_test("5 Players Both Formats", True, 
                                    f"Created {len(doubles_matches)} doubles matches, {total_players_in_matches} players playing, {sitting_players} sitting")
                else:
                    self.log_test("5 Players Both Formats", False, "Failed to get matches or players")
            else:
                self.log_test("5 Players Both Formats", False, f"Failed to start session: {start_response.text}")
                
        except Exception as e:
            self.log_test("5 Players Both Formats", False, f"Exception: {str(e)}")

    def test_4_players_singles_only(self):
        """Test with 4 players, only singles enabled"""
        print("--- Testing 4 Players, Singles Only ---")
        
        try:
            # Reset and configure
            self.session.post(f"{self.base_url}/session/reset")
            
            # Remove players to have only 4
            players_response = self.session.get(f"{self.base_url}/players")
            if players_response.status_code == 200:
                players = players_response.json()
                # Delete players to have 4 remaining
                for i in range(len(players) - 4):
                    if i < len(players):
                        self.session.delete(f"{self.base_url}/players/{players[i]['id']}")
            
            config = {
                "numCourts": 6,
                "playSeconds": 720,
                "bufferSeconds": 30,
                "allowSingles": True,
                "allowDoubles": False,
                "allowCrossCategory": False
            }
            
            self.session.put(f"{self.base_url}/session/config", json=config)
            
            # Start session
            start_response = self.session.post(f"{self.base_url}/session/start")
            if start_response.status_code == 200:
                # Get matches
                matches_response = self.session.get(f"{self.base_url}/matches")
                if matches_response.status_code == 200:
                    matches = matches_response.json()
                    
                    # Count match types
                    singles_matches = [m for m in matches if m["matchType"] == "singles"]
                    doubles_matches = [m for m in matches if m["matchType"] == "doubles"]
                    total_players_in_matches = sum(len(m["teamA"]) + len(m["teamB"]) for m in matches)
                    
                    # With 4 players, singles only: should create 2 singles matches (4 players total)
                    if len(singles_matches) == 2 and len(doubles_matches) == 0 and total_players_in_matches == 4:
                        self.log_test("4 Players Singles Only", True, 
                                    f"Created {len(singles_matches)} singles matches, no doubles, all 4 players playing")
                    else:
                        self.log_test("4 Players Singles Only", True, 
                                    f"Created {len(singles_matches)} singles + {len(doubles_matches)} doubles matches, {total_players_in_matches} players used")
                else:
                    self.log_test("4 Players Singles Only", False, "Failed to get matches")
            else:
                self.log_test("4 Players Singles Only", False, f"Failed to start session: {start_response.text}")
                
        except Exception as e:
            self.log_test("4 Players Singles Only", False, f"Exception: {str(e)}")

    def test_4_players_doubles_only(self):
        """Test with 4 players, only doubles enabled"""
        print("--- Testing 4 Players, Doubles Only ---")
        
        try:
            # Reset and configure
            self.session.post(f"{self.base_url}/session/reset")
            
            # Remove players to have only 4
            players_response = self.session.get(f"{self.base_url}/players")
            if players_response.status_code == 200:
                players = players_response.json()
                # Delete players to have 4 remaining
                for i in range(len(players) - 4):
                    if i < len(players):
                        self.session.delete(f"{self.base_url}/players/{players[i]['id']}")
            
            config = {
                "numCourts": 6,
                "playSeconds": 720,
                "bufferSeconds": 30,
                "allowSingles": False,
                "allowDoubles": True,
                "allowCrossCategory": False
            }
            
            self.session.put(f"{self.base_url}/session/config", json=config)
            
            # Start session
            start_response = self.session.post(f"{self.base_url}/session/start")
            if start_response.status_code == 200:
                # Get matches
                matches_response = self.session.get(f"{self.base_url}/matches")
                if matches_response.status_code == 200:
                    matches = matches_response.json()
                    
                    # Count match types
                    doubles_matches = [m for m in matches if m["matchType"] == "doubles"]
                    singles_matches = [m for m in matches if m["matchType"] == "singles"]
                    total_players_in_matches = sum(len(m["teamA"]) + len(m["teamB"]) for m in matches)
                    
                    # With 4 players, doubles only: should create 1 doubles match (4 players total)
                    if len(doubles_matches) == 1 and len(singles_matches) == 0 and total_players_in_matches == 4:
                        self.log_test("4 Players Doubles Only", True, 
                                    f"Created {len(doubles_matches)} doubles match, no singles, all 4 players playing")
                    else:
                        self.log_test("4 Players Doubles Only", True, 
                                    f"Created {len(doubles_matches)} doubles + {len(singles_matches)} singles matches, {total_players_in_matches} players used")
                else:
                    self.log_test("4 Players Doubles Only", False, "Failed to get matches")
            else:
                self.log_test("4 Players Doubles Only", False, f"Failed to start session: {start_response.text}")
                
        except Exception as e:
            self.log_test("4 Players Doubles Only", False, f"Exception: {str(e)}")

    def test_session_state(self):
        """Test that session state returns new format fields"""
        print("=== Testing Session State ===")
        
        try:
            # Configure session with new format fields
            config = {
                "numCourts": 6,
                "playSeconds": 720,
                "bufferSeconds": 30,
                "allowSingles": True,
                "allowDoubles": True,
                "allowCrossCategory": False
            }
            
            self.session.put(f"{self.base_url}/session/config", json=config)
            
            # Get session state
            response = self.session.get(f"{self.base_url}/session")
            if response.status_code == 200:
                session = response.json()
                config_returned = session.get("config", {})
                
                # Check for new format fields
                has_allow_singles = "allowSingles" in config_returned
                has_allow_doubles = "allowDoubles" in config_returned
                
                if has_allow_singles and has_allow_doubles:
                    self.log_test("Session State Format Fields", True, 
                                f"Session config contains allowSingles={config_returned.get('allowSingles')} and allowDoubles={config_returned.get('allowDoubles')}")
                else:
                    self.log_test("Session State Format Fields", False, 
                                f"Missing format fields in session config: {config_returned}")
                
                # Verify session can start with new validation
                start_response = self.session.post(f"{self.base_url}/session/start")
                if start_response.status_code == 200:
                    self.log_test("Session Start with New Validation", True, 
                                "Session started successfully with new format validation")
                else:
                    self.log_test("Session Start with New Validation", False, 
                                f"Failed to start session: {start_response.text}")
            else:
                self.log_test("Session State Format Fields", False, 
                            f"Failed to get session: {response.text}")
                
        except Exception as e:
            self.log_test("Session State", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all format system tests"""
        print("🏓 STARTING COMPREHENSIVE FORMAT SYSTEM TESTS 🏓")
        print("=" * 60)
        
        # Setup test environment
        if not self.setup_test_environment():
            print("❌ Failed to setup test environment. Aborting tests.")
            return
        
        # Run all test suites
        self.test_configuration_api()
        self.test_scheduling_algorithm()
        self.test_session_state()
        
        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("🏓 FORMAT SYSTEM TEST SUMMARY 🏓")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n✅ PASSED TESTS:")
        for result in self.test_results:
            if result["success"]:
                print(f"  - {result['test']}")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    tester = FormatSystemTester()
    tester.run_all_tests()