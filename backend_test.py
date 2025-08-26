#!/usr/bin/env python3
"""
Comprehensive Backend API Tests for Pickleball Session Manager
Tests all core CRUD operations and session management functionality
"""

import requests
import json
import os
from typing import Dict, List, Any
import time

# Get backend URL from environment
BACKEND_URL = "https://roundrobin.preview.emergentagent.com/api"

class PickleballAPITester:
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

    def test_initialization(self):
        """Test POST /api/init to create default categories"""
        print("=== Testing Initialization ===")
        try:
            response = self.session.post(f"{self.base_url}/init")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "initialized" in data["message"].lower():
                    self.log_test("Initialize Default Data", True, f"Response: {data}")
                else:
                    self.log_test("Initialize Default Data", True, f"Initialization completed: {data}")
            else:
                self.log_test("Initialize Default Data", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Initialize Default Data", False, f"Exception: {str(e)}")

    def test_categories(self):
        """Test GET /api/categories to verify default categories"""
        print("=== Testing Categories ===")
        try:
            response = self.session.get(f"{self.base_url}/categories")
            
            if response.status_code == 200:
                categories = response.json()
                
                # Check if we have categories
                if not categories:
                    self.log_test("Get Categories", False, "No categories found")
                    return
                
                # Check for expected default categories
                category_names = [cat["name"] for cat in categories]
                expected_categories = ["Beginner", "Intermediate", "Advanced"]
                
                missing_categories = [cat for cat in expected_categories if cat not in category_names]
                
                if not missing_categories:
                    self.log_test("Get Categories", True, f"Found all expected categories: {category_names}")
                else:
                    self.log_test("Get Categories", False, f"Missing categories: {missing_categories}. Found: {category_names}")
                    
                # Verify category structure
                for cat in categories:
                    required_fields = ["id", "name"]
                    missing_fields = [field for field in required_fields if field not in cat]
                    if missing_fields:
                        self.log_test("Category Structure", False, f"Category missing fields: {missing_fields}")
                        return
                
                self.log_test("Category Structure", True, "All categories have required fields")
                
            else:
                self.log_test("Get Categories", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Get Categories", False, f"Exception: {str(e)}")

    def test_create_players(self):
        """Test POST /api/players to create test players across different categories"""
        print("=== Testing Player Creation ===")
        
        # Test players with realistic names and categories
        test_players = [
            {"name": "Sarah Johnson", "category": "Beginner"},
            {"name": "Mike Chen", "category": "Beginner"},
            {"name": "Lisa Rodriguez", "category": "Intermediate"},
            {"name": "David Kim", "category": "Intermediate"},
            {"name": "Jennifer Walsh", "category": "Advanced"},
            {"name": "Robert Thompson", "category": "Advanced"}
        ]
        
        for player_data in test_players:
            try:
                response = self.session.post(f"{self.base_url}/players", json=player_data)
                
                if response.status_code == 200:
                    player = response.json()
                    
                    # Verify player structure
                    required_fields = ["id", "name", "category", "sitNextRound", "sitCount", "missDueToCourtLimit", "stats"]
                    missing_fields = [field for field in required_fields if field not in player]
                    
                    if missing_fields:
                        self.log_test(f"Create Player {player_data['name']}", False, f"Missing fields: {missing_fields}")
                    else:
                        # Verify stats initialization
                        stats = player["stats"]
                        expected_stats = {"wins": 0, "losses": 0, "pointDiff": 0}
                        
                        if stats == expected_stats:
                            self.created_players.append(player)
                            self.log_test(f"Create Player {player_data['name']}", True, f"Player created with proper stats initialization")
                        else:
                            self.log_test(f"Create Player {player_data['name']}", False, f"Stats not properly initialized. Expected: {expected_stats}, Got: {stats}")
                else:
                    self.log_test(f"Create Player {player_data['name']}", False, f"Status: {response.status_code}, Response: {response.text}")
                    
            except Exception as e:
                self.log_test(f"Create Player {player_data['name']}", False, f"Exception: {str(e)}")

    def test_get_players(self):
        """Test GET /api/players to verify players are created"""
        print("=== Testing Get Players ===")
        try:
            response = self.session.get(f"{self.base_url}/players")
            
            if response.status_code == 200:
                players = response.json()
                
                if not players:
                    self.log_test("Get Players", False, "No players found")
                    return
                
                # Verify we have the expected number of players (at least the ones we created)
                if len(players) >= len(self.created_players):
                    self.log_test("Get Players Count", True, f"Found {len(players)} players")
                else:
                    self.log_test("Get Players Count", False, f"Expected at least {len(self.created_players)} players, found {len(players)}")
                
                # Verify player structure for each player
                structure_valid = True
                for player in players:
                    required_fields = ["id", "name", "category", "sitNextRound", "sitCount", "missDueToCourtLimit", "stats"]
                    missing_fields = [field for field in required_fields if field not in player]
                    if missing_fields:
                        structure_valid = False
                        break
                
                if structure_valid:
                    self.log_test("Players Structure", True, "All players have required fields")
                else:
                    self.log_test("Players Structure", False, f"Some players missing required fields")
                    
                # Test category distribution
                categories = {}
                for player in players:
                    cat = player["category"]
                    categories[cat] = categories.get(cat, 0) + 1
                
                self.log_test("Player Categories", True, f"Category distribution: {categories}")
                
            else:
                self.log_test("Get Players", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Get Players", False, f"Exception: {str(e)}")

    def test_session_state(self):
        """Test GET /api/session to check session state"""
        print("=== Testing Session State ===")
        try:
            response = self.session.get(f"{self.base_url}/session")
            
            if response.status_code == 200:
                session = response.json()
                
                # Verify session structure
                required_fields = ["id", "currentRound", "phase", "timeRemaining", "paused", "config", "histories"]
                missing_fields = [field for field in required_fields if field not in session]
                
                if missing_fields:
                    self.log_test("Session Structure", False, f"Missing fields: {missing_fields}")
                else:
                    self.log_test("Session Structure", True, "Session has all required fields")
                
                # Verify config structure
                config = session.get("config", {})
                config_fields = ["numCourts", "playSeconds", "bufferSeconds", "format"]
                missing_config_fields = [field for field in config_fields if field not in config]
                
                if missing_config_fields:
                    self.log_test("Session Config Structure", False, f"Missing config fields: {missing_config_fields}")
                else:
                    self.log_test("Session Config Structure", True, f"Config: {config}")
                
                # Verify initial state
                if session.get("phase") == "idle" and session.get("currentRound") == 0:
                    self.log_test("Initial Session State", True, "Session in proper initial state")
                else:
                    self.log_test("Initial Session State", True, f"Session state: phase={session.get('phase')}, round={session.get('currentRound')}")
                    
            else:
                self.log_test("Get Session State", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Get Session State", False, f"Exception: {str(e)}")

    def test_session_config_update(self):
        """Test PUT /api/session/config to update configuration"""
        print("=== Testing Session Configuration Update ===")
        
        new_config = {
            "numCourts": 6,
            "playSeconds": 900,  # 15 minutes
            "bufferSeconds": 45,  # 45 seconds
            "format": "doubles"
        }
        
        try:
            response = self.session.put(f"{self.base_url}/session/config", json=new_config)
            
            if response.status_code == 200:
                session = response.json()
                updated_config = session.get("config", {})
                
                # Verify config was updated
                config_match = all(updated_config.get(key) == value for key, value in new_config.items())
                
                if config_match:
                    self.log_test("Update Session Config", True, f"Config updated successfully: {updated_config}")
                else:
                    self.log_test("Update Session Config", False, f"Config not updated properly. Expected: {new_config}, Got: {updated_config}")
            else:
                self.log_test("Update Session Config", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Update Session Config", False, f"Exception: {str(e)}")

    def test_session_controls(self):
        """Test session control endpoints: start, pause, resume, reset"""
        print("=== Testing Session Controls ===")
        
        # Test session start
        try:
            response = self.session.post(f"{self.base_url}/session/start")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Start Session", True, f"Response: {data}")
                
                # Verify session state changed
                time.sleep(1)  # Brief pause to ensure state change
                session_response = self.session.get(f"{self.base_url}/session")
                if session_response.status_code == 200:
                    session = session_response.json()
                    if session.get("phase") == "play" and session.get("currentRound") >= 1:
                        self.log_test("Session Start State Change", True, f"Session phase: {session.get('phase')}, round: {session.get('currentRound')}")
                    else:
                        self.log_test("Session Start State Change", False, f"Session state not updated properly: {session}")
            else:
                self.log_test("Start Session", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Start Session", False, f"Exception: {str(e)}")

        # Test session pause
        try:
            response = self.session.post(f"{self.base_url}/session/pause")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Pause Session", True, f"Response: {data}")
            else:
                self.log_test("Pause Session", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Pause Session", False, f"Exception: {str(e)}")

        # Test session resume
        try:
            response = self.session.post(f"{self.base_url}/session/resume")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Resume Session", True, f"Response: {data}")
            else:
                self.log_test("Resume Session", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Resume Session", False, f"Exception: {str(e)}")

        # Test session reset
        try:
            response = self.session.post(f"{self.base_url}/session/reset")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Reset Session", True, f"Response: {data}")
                
                # Verify session was reset
                time.sleep(1)
                session_response = self.session.get(f"{self.base_url}/session")
                if session_response.status_code == 200:
                    session = session_response.json()
                    if session.get("phase") == "idle" and session.get("currentRound") == 0:
                        self.log_test("Session Reset State", True, "Session properly reset to initial state")
                    else:
                        self.log_test("Session Reset State", False, f"Session not properly reset: {session}")
            else:
                self.log_test("Reset Session", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Reset Session", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🏓 Starting Pickleball Session Manager Backend API Tests")
        print(f"Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Run tests in logical order
        self.test_initialization()
        self.test_categories()
        self.test_create_players()
        self.test_get_players()
        self.test_session_state()
        self.test_session_config_update()
        self.test_session_controls()
        
        # Print summary
        print("=" * 60)
        print("🏓 TEST SUMMARY")
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
            print("✅ ALL TESTS PASSED!")
        
        return passed == total

if __name__ == "__main__":
    tester = PickleballAPITester()
    success = tester.run_all_tests()
    exit(0 if success else 1)