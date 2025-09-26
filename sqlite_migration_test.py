#!/usr/bin/env python3
"""
SQLite Migration Test for CourtChime Backend APIs
Tests the migration progress from MongoDB to SQLite
"""

import requests
import json
import os
from typing import Dict, List, Any
import time

# Get backend URL from environment
BACKEND_URL = "https://court-timer.preview.emergentagent.com/api"

class SQLiteMigrationTester:
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

    def test_data_management_apis(self):
        """Test Data Management APIs (Migrated to SQLite)"""
        print("=== Testing Data Management APIs (SQLite) ===")
        
        # Test 1: Clear all data
        try:
            response = self.session.delete(f"{self.base_url}/clear-all-data")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "cleared" in data["message"].lower():
                    self.log_test("Clear All Data (SQLite)", True, f"Response: {data}")
                else:
                    self.log_test("Clear All Data (SQLite)", True, f"Data cleared: {data}")
            else:
                self.log_test("Clear All Data (SQLite)", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Clear All Data (SQLite)", False, f"Exception: {str(e)}")

        # Test 2: Add test data
        try:
            response = self.session.post(f"{self.base_url}/add-test-data")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "added" in data["message"].lower():
                    self.log_test("Add Test Data (SQLite)", True, f"Response: {data}")
                else:
                    self.log_test("Add Test Data (SQLite)", True, f"Test data added: {data}")
            else:
                self.log_test("Add Test Data (SQLite)", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Add Test Data (SQLite)", False, f"Exception: {str(e)}")

    def test_players_apis_sqlite(self):
        """Test Players APIs (Migrated to SQLite)"""
        print("=== Testing Players APIs (SQLite) ===")
        
        # Test 1: GET /api/players - should return test players with DUPR ratings
        try:
            response = self.session.get(f"{self.base_url}/players")
            
            if response.status_code == 200:
                players = response.json()
                
                if len(players) >= 12:
                    self.log_test("GET Players (SQLite)", True, f"Found {len(players)} players with DUPR ratings")
                    
                    # Verify DUPR fields
                    dupr_fields_valid = True
                    for player in players:
                        required_dupr_fields = ["rating", "matchesPlayed", "wins", "losses", "recentForm", "ratingHistory"]
                        missing_fields = [field for field in required_dupr_fields if field not in player]
                        if missing_fields:
                            dupr_fields_valid = False
                            self.log_test("DUPR Fields Validation", False, f"Player {player['name']} missing DUPR fields: {missing_fields}")
                            break
                    
                    if dupr_fields_valid:
                        self.log_test("DUPR Fields Validation", True, "All players have required DUPR rating fields")
                        
                        # Check rating ranges (should be 2.0-8.0)
                        rating_ranges_valid = True
                        for player in players:
                            rating = player.get("rating", 0)
                            if not (2.0 <= rating <= 8.0):
                                rating_ranges_valid = False
                                self.log_test("DUPR Rating Range", False, f"Player {player['name']} has invalid rating: {rating}")
                                break
                        
                        if rating_ranges_valid:
                            self.log_test("DUPR Rating Range", True, "All player ratings within valid DUPR range (2.0-8.0)")
                    
                    # Store first player for update/delete tests
                    if players:
                        self.created_players = players
                        
                else:
                    self.log_test("GET Players (SQLite)", False, f"Expected at least 12 players, found {len(players)}")
                    
            else:
                self.log_test("GET Players (SQLite)", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("GET Players (SQLite)", False, f"Exception: {str(e)}")

        # Test 2: POST /api/players - create new player
        try:
            new_player = {
                "name": "Test Player SQLite",
                "category": "Intermediate"
            }
            
            response = self.session.post(f"{self.base_url}/players", json=new_player)
            
            if response.status_code == 200:
                player = response.json()
                
                # Verify player structure
                required_fields = ["id", "name", "category", "rating", "matchesPlayed", "wins", "losses"]
                missing_fields = [field for field in required_fields if field not in player]
                
                if not missing_fields:
                    self.log_test("POST Players (SQLite)", True, f"Created player: {player['name']} with rating {player['rating']}")
                    self.created_players.append(player)
                else:
                    self.log_test("POST Players (SQLite)", False, f"Created player missing fields: {missing_fields}")
            else:
                self.log_test("POST Players (SQLite)", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("POST Players (SQLite)", False, f"Exception: {str(e)}")

        # Test 3: PUT /api/players/{id} - update player
        if self.created_players:
            try:
                player_to_update = self.created_players[0]
                player_id = player_to_update["id"]
                
                update_data = {
                    "name": "Updated Player Name",
                    "category": "Advanced"
                }
                
                response = self.session.put(f"{self.base_url}/players/{player_id}", json=update_data)
                
                if response.status_code == 200:
                    updated_player = response.json()
                    
                    if updated_player["name"] == update_data["name"] and updated_player["category"] == update_data["category"]:
                        self.log_test("PUT Players (SQLite)", True, f"Updated player: {updated_player['name']} -> {updated_player['category']}")
                    else:
                        self.log_test("PUT Players (SQLite)", False, f"Player not updated correctly: {updated_player}")
                else:
                    self.log_test("PUT Players (SQLite)", False, f"Status: {response.status_code}, Response: {response.text}")
                    
            except Exception as e:
                self.log_test("PUT Players (SQLite)", False, f"Exception: {str(e)}")

        # Test 4: DELETE /api/players/{id} - delete player
        if len(self.created_players) > 1:
            try:
                player_to_delete = self.created_players[-1]  # Delete the last one we created
                player_id = player_to_delete["id"]
                
                response = self.session.delete(f"{self.base_url}/players/{player_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    if "message" in data and "deleted" in data["message"].lower():
                        self.log_test("DELETE Players (SQLite)", True, f"Deleted player: {player_to_delete['name']}")
                    else:
                        self.log_test("DELETE Players (SQLite)", True, f"Player deleted: {data}")
                else:
                    self.log_test("DELETE Players (SQLite)", False, f"Status: {response.status_code}, Response: {response.text}")
                    
            except Exception as e:
                self.log_test("DELETE Players (SQLite)", False, f"Exception: {str(e)}")

    def test_categories_apis_sqlite(self):
        """Test Categories APIs (Migrated to SQLite)"""
        print("=== Testing Categories APIs (SQLite) ===")
        
        # Test 1: GET /api/categories - should return default categories
        try:
            response = self.session.get(f"{self.base_url}/categories")
            
            if response.status_code == 200:
                categories = response.json()
                
                # Check for expected default categories
                category_names = [cat["name"] for cat in categories]
                expected_categories = ["Beginner", "Intermediate", "Advanced"]
                
                missing_categories = [cat for cat in expected_categories if cat not in category_names]
                
                if not missing_categories:
                    self.log_test("GET Categories (SQLite)", True, f"Found all expected categories: {category_names}")
                else:
                    self.log_test("GET Categories (SQLite)", False, f"Missing categories: {missing_categories}. Found: {category_names}")
                    
            else:
                self.log_test("GET Categories (SQLite)", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("GET Categories (SQLite)", False, f"Exception: {str(e)}")

        # Test 2: POST /api/categories - create new category
        try:
            new_category = {
                "name": "Expert",
                "description": "Expert level players"
            }
            
            response = self.session.post(f"{self.base_url}/categories", json=new_category)
            
            if response.status_code == 200:
                category = response.json()
                
                if category["name"] == new_category["name"]:
                    self.log_test("POST Categories (SQLite)", True, f"Created category: {category['name']}")
                    
                    # Test 3: DELETE /api/categories/{id} - delete the category we just created
                    try:
                        category_id = category["id"]
                        delete_response = self.session.delete(f"{self.base_url}/categories/{category_id}")
                        
                        if delete_response.status_code == 200:
                            data = delete_response.json()
                            if "message" in data and "deleted" in data["message"].lower():
                                self.log_test("DELETE Categories (SQLite)", True, f"Deleted category: {category['name']}")
                            else:
                                self.log_test("DELETE Categories (SQLite)", True, f"Category deleted: {data}")
                        else:
                            self.log_test("DELETE Categories (SQLite)", False, f"Status: {delete_response.status_code}, Response: {delete_response.text}")
                            
                    except Exception as e:
                        self.log_test("DELETE Categories (SQLite)", False, f"Exception: {str(e)}")
                        
                else:
                    self.log_test("POST Categories (SQLite)", False, f"Category not created correctly: {category}")
            else:
                self.log_test("POST Categories (SQLite)", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("POST Categories (SQLite)", False, f"Exception: {str(e)}")

    def test_matches_apis_sqlite(self):
        """Test Matches APIs (Partially Migrated to SQLite)"""
        print("=== Testing Matches APIs (Partially SQLite) ===")
        
        # Test 1: GET /api/matches - should return empty list initially
        try:
            response = self.session.get(f"{self.base_url}/matches")
            
            if response.status_code == 200:
                matches = response.json()
                
                # Should be empty initially or contain matches from previous tests
                self.log_test("GET Matches (SQLite)", True, f"Retrieved {len(matches)} matches from SQLite")
                
                # Verify match structure if any matches exist
                if matches:
                    match = matches[0]
                    required_fields = ["id", "roundIndex", "courtIndex", "category", "teamA", "teamB", "status", "matchType"]
                    missing_fields = [field for field in required_fields if field not in match]
                    
                    if not missing_fields:
                        self.log_test("Match Structure (SQLite)", True, "Match structure valid with JSON field parsing")
                    else:
                        self.log_test("Match Structure (SQLite)", False, f"Match missing fields: {missing_fields}")
                        
            else:
                self.log_test("GET Matches (SQLite)", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("GET Matches (SQLite)", False, f"Exception: {str(e)}")

        # Test 2: GET /api/matches/round/1 - should return empty list for round 1
        try:
            response = self.session.get(f"{self.base_url}/matches/round/1")
            
            if response.status_code == 200:
                matches = response.json()
                self.log_test("GET Matches by Round (SQLite)", True, f"Retrieved {len(matches)} matches for round 1")
            else:
                self.log_test("GET Matches by Round (SQLite)", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("GET Matches by Round (SQLite)", False, f"Exception: {str(e)}")

    def test_session_apis_mongodb(self):
        """Test Session APIs (Still use MongoDB - expect to work but with MongoDB)"""
        print("=== Testing Session APIs (MongoDB - Expected to Work) ===")
        
        # Test 1: GET /api/session
        try:
            response = self.session.get(f"{self.base_url}/session")
            
            if response.status_code == 200:
                session = response.json()
                
                # Verify session structure
                required_fields = ["id", "currentRound", "phase", "timeRemaining", "paused", "config"]
                missing_fields = [field for field in required_fields if field not in session]
                
                if not missing_fields:
                    self.log_test("GET Session (MongoDB)", True, f"Session retrieved successfully: phase={session.get('phase')}, round={session.get('currentRound')}")
                else:
                    self.log_test("GET Session (MongoDB)", False, f"Session missing fields: {missing_fields}")
                    
            else:
                self.log_test("GET Session (MongoDB)", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("GET Session (MongoDB)", False, f"Exception: {str(e)}")

        # Test 2: PUT /api/session/config
        try:
            new_config = {
                "numCourts": 6,
                "playSeconds": 720,
                "bufferSeconds": 30,
                "allowSingles": True,
                "allowDoubles": True,
                "allowCrossCategory": False,
                "maximizeCourtUsage": False
            }
            
            response = self.session.put(f"{self.base_url}/session/config", json=new_config)
            
            if response.status_code == 200:
                session = response.json()
                updated_config = session.get("config", {})
                
                # Verify config was updated
                config_match = all(updated_config.get(key) == value for key, value in new_config.items())
                
                if config_match:
                    self.log_test("PUT Session Config (MongoDB)", True, f"Config updated successfully")
                else:
                    self.log_test("PUT Session Config (MongoDB)", False, f"Config not updated properly")
            else:
                self.log_test("PUT Session Config (MongoDB)", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("PUT Session Config (MongoDB)", False, f"Exception: {str(e)}")

    def test_mixed_apis_integration(self):
        """Test integration between SQLite and MongoDB APIs"""
        print("=== Testing Mixed SQLite/MongoDB Integration ===")
        
        try:
            # Clear data and add test data (SQLite)
            self.session.delete(f"{self.base_url}/clear-all-data")
            self.session.post(f"{self.base_url}/add-test-data")
            
            # Get players (SQLite)
            players_response = self.session.get(f"{self.base_url}/players")
            
            # Get session (MongoDB)
            session_response = self.session.get(f"{self.base_url}/session")
            
            if players_response.status_code == 200 and session_response.status_code == 200:
                players = players_response.json()
                session = session_response.json()
                
                self.log_test("Mixed Integration Test", True, f"Successfully retrieved {len(players)} players (SQLite) and session data (MongoDB)")
                
                # Test if we can start a session with SQLite players
                # Note: This might fail because session management still uses MongoDB
                try:
                    start_response = self.session.post(f"{self.base_url}/session/start")
                    if start_response.status_code == 200:
                        self.log_test("Session Start with SQLite Players", True, "Session started successfully with SQLite players")
                    else:
                        self.log_test("Session Start with SQLite Players", False, f"Failed to start session: {start_response.status_code} - {start_response.text}")
                except Exception as e:
                    self.log_test("Session Start with SQLite Players", False, f"Exception during session start: {str(e)}")
                    
            else:
                self.log_test("Mixed Integration Test", False, "Failed to retrieve data from both SQLite and MongoDB")
                
        except Exception as e:
            self.log_test("Mixed Integration Test", False, f"Exception: {str(e)}")

    def test_database_initialization(self):
        """Test database initialization and data persistence"""
        print("=== Testing Database Initialization ===")
        
        try:
            # Clear all data first
            clear_response = self.session.delete(f"{self.base_url}/clear-all-data")
            
            if clear_response.status_code == 200:
                self.log_test("Database Clear", True, "Database cleared successfully")
                
                # Check that categories are reinitialized
                categories_response = self.session.get(f"{self.base_url}/categories")
                if categories_response.status_code == 200:
                    categories = categories_response.json()
                    expected_categories = ["Beginner", "Intermediate", "Advanced"]
                    category_names = [cat["name"] for cat in categories]
                    
                    if all(cat in category_names for cat in expected_categories):
                        self.log_test("Database Reinitialization", True, "Default categories reinitialized after clear")
                    else:
                        self.log_test("Database Reinitialization", False, f"Categories not reinitialized properly: {category_names}")
                else:
                    self.log_test("Database Reinitialization", False, "Failed to retrieve categories after clear")
                    
                # Check that players are cleared
                players_response = self.session.get(f"{self.base_url}/players")
                if players_response.status_code == 200:
                    players = players_response.json()
                    if len(players) == 0:
                        self.log_test("Players Clear Verification", True, "Players cleared successfully")
                    else:
                        self.log_test("Players Clear Verification", False, f"Players not cleared: {len(players)} remaining")
                else:
                    self.log_test("Players Clear Verification", False, "Failed to verify players clear")
                    
            else:
                self.log_test("Database Clear", False, f"Failed to clear database: {clear_response.status_code}")
                
        except Exception as e:
            self.log_test("Database Initialization", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all SQLite migration tests"""
        print("🔄 Starting SQLite Migration Tests for CourtChime Backend")
        print(f"Backend URL: {self.base_url}")
        print("=" * 80)
        
        # Test order based on dependencies
        self.test_database_initialization()
        self.test_data_management_apis()
        self.test_categories_apis_sqlite()
        self.test_players_apis_sqlite()
        self.test_matches_apis_sqlite()
        self.test_session_apis_mongodb()
        self.test_mixed_apis_integration()
        
        # Print summary
        print("=" * 80)
        print("🏁 SQLite Migration Test Summary")
        print("=" * 80)
        
        passed_tests = [r for r in self.test_results if r["success"]]
        failed_tests = [r for r in self.test_results if not r["success"]]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📊 TOTAL: {len(self.test_results)}")
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   • {test['test']}: {test['details']}")
        
        if passed_tests:
            print(f"\n✅ PASSED TESTS: {len(passed_tests)} tests passed successfully")
        
        success_rate = (len(passed_tests) / len(self.test_results)) * 100 if self.test_results else 0
        print(f"\n📈 SUCCESS RATE: {success_rate:.1f}%")
        
        return len(failed_tests) == 0

if __name__ == "__main__":
    tester = SQLiteMigrationTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All SQLite migration tests passed!")
    else:
        print("\n⚠️  Some SQLite migration tests failed. Check the details above.")