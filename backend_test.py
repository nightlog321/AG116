#!/usr/bin/env python3
"""
CourtChime Backend API Test Suite
Tests all core backend functionality including player management, 
session control, match generation, and database operations.
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any, Optional

# Backend URL from environment
BACKEND_URL = "https://court-manager-9.preview.emergentagent.com/api"

class CourtChimeAPITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.created_players = []
        self.created_categories = []
        
    def log_test(self, test_name: str, success: bool, message: str, details: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def test_health_check(self):
        """Test if backend is accessible"""
        try:
            response = self.session.get(f"{self.base_url}/categories")
            if response.status_code == 200:
                self.log_test("Health Check", True, "Backend is accessible")
                return True
            else:
                self.log_test("Health Check", False, f"Backend returned status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Check", False, f"Cannot connect to backend: {str(e)}")
            return False
    
    def test_categories_api(self):
        """Test categories CRUD operations"""
        try:
            # Test GET categories
            response = self.session.get(f"{self.base_url}/categories")
            if response.status_code != 200:
                self.log_test("Categories GET", False, f"Status: {response.status_code}", response.text)
                return False
            
            categories = response.json()
            self.log_test("Categories GET", True, f"Retrieved {len(categories)} categories")
            
            # Test POST category
            test_category = {
                "name": "Test Category",
                "description": "Test category for API testing"
            }
            
            response = self.session.post(f"{self.base_url}/categories", json=test_category)
            if response.status_code == 200:
                created_category = response.json()
                self.created_categories.append(created_category["id"])
                self.log_test("Categories POST", True, f"Created category: {created_category['name']}")
            else:
                self.log_test("Categories POST", False, f"Status: {response.status_code}", response.text)
                
            return True
            
        except Exception as e:
            self.log_test("Categories API", False, f"Exception: {str(e)}")
            return False
    
    def test_players_api(self):
        """Test players CRUD operations with focus on isActive field"""
        try:
            # Test GET players
            response = self.session.get(f"{self.base_url}/players")
            if response.status_code != 200:
                self.log_test("Players GET", False, f"Status: {response.status_code}", response.text)
                return False
            
            players = response.json()
            self.log_test("Players GET", True, f"Retrieved {len(players)} players")
            
            # Verify isActive field is present in all players
            active_field_present = all("isActive" in player for player in players)
            if active_field_present:
                active_count = sum(1 for player in players if player.get("isActive", False))
                self.log_test("Players isActive Field", True, f"isActive field present in all players. {active_count}/{len(players)} active")
            else:
                self.log_test("Players isActive Field", False, "isActive field missing in some players")
            
            # Test POST player
            test_player = {
                "name": "Test Player API",
                "category": "Beginner"
            }
            
            response = self.session.post(f"{self.base_url}/players", json=test_player)
            if response.status_code == 200:
                created_player = response.json()
                self.created_players.append(created_player["id"])
                
                # Verify new player has isActive field set to True by default
                if created_player.get("isActive", False):
                    self.log_test("Players POST", True, f"Created player: {created_player['name']} with isActive=True")
                else:
                    self.log_test("Players POST", False, f"Created player but isActive field is {created_player.get('isActive')}")
                
                return created_player
            else:
                self.log_test("Players POST", False, f"Status: {response.status_code}", response.text)
                return None
                
        except Exception as e:
            self.log_test("Players API", False, f"Exception: {str(e)}")
            return None
    
    def test_player_toggle_active(self, player_id: str):
        """Test the critical toggle-active endpoint"""
        try:
            # First, get current player state
            response = self.session.get(f"{self.base_url}/players")
            if response.status_code != 200:
                self.log_test("Toggle Active - Get Initial State", False, f"Cannot get players: {response.status_code}")
                return False
            
            players = response.json()
            target_player = next((p for p in players if p["id"] == player_id), None)
            if not target_player:
                self.log_test("Toggle Active - Find Player", False, f"Player {player_id} not found")
                return False
            
            initial_active_state = target_player.get("isActive", True)
            self.log_test("Toggle Active - Initial State", True, f"Player {target_player['name']} isActive: {initial_active_state}")
            
            # Test toggle endpoint
            response = self.session.patch(f"{self.base_url}/players/{player_id}/toggle-active")
            if response.status_code != 200:
                self.log_test("Toggle Active - API Call", False, f"Status: {response.status_code}", response.text)
                return False
            
            toggle_response = response.json()
            expected_new_state = not initial_active_state
            returned_state = toggle_response.get("isActive")
            
            if returned_state == expected_new_state:
                self.log_test("Toggle Active - Response", True, f"Toggle response correct: {returned_state}")
            else:
                self.log_test("Toggle Active - Response", False, f"Expected {expected_new_state}, got {returned_state}")
                return False
            
            # Verify persistence by getting players again
            time.sleep(0.5)  # Small delay to ensure database write
            response = self.session.get(f"{self.base_url}/players")
            if response.status_code != 200:
                self.log_test("Toggle Active - Verify Persistence", False, f"Cannot get players after toggle: {response.status_code}")
                return False
            
            updated_players = response.json()
            updated_player = next((p for p in updated_players if p["id"] == player_id), None)
            
            if updated_player and updated_player.get("isActive") == expected_new_state:
                self.log_test("Toggle Active - Database Persistence", True, f"Database correctly updated: isActive={expected_new_state}")
            else:
                actual_state = updated_player.get("isActive") if updated_player else "player not found"
                self.log_test("Toggle Active - Database Persistence", False, f"Database not updated correctly. Expected {expected_new_state}, got {actual_state}")
                return False
            
            # Toggle back to original state
            response = self.session.patch(f"{self.base_url}/players/{player_id}/toggle-active")
            if response.status_code == 200:
                self.log_test("Toggle Active - Toggle Back", True, "Successfully toggled back to original state")
            else:
                self.log_test("Toggle Active - Toggle Back", False, f"Failed to toggle back: {response.status_code}")
            
            return True
            
        except Exception as e:
            self.log_test("Toggle Active", False, f"Exception: {str(e)}")
            return False
    
    def test_session_api(self):
        """Test session control endpoints"""
        try:
            # Test GET session
            response = self.session.get(f"{self.base_url}/session")
            if response.status_code != 200:
                self.log_test("Session GET", False, f"Status: {response.status_code}", response.text)
                return False
            
            session_data = response.json()
            self.log_test("Session GET", True, f"Session phase: {session_data.get('phase', 'unknown')}")
            
            # Test session configuration
            response = self.session.get(f"{self.base_url}/session/config")
            if response.status_code == 200:
                config = response.json()
                self.log_test("Session Config", True, f"Courts: {config.get('numCourts', 'unknown')}")
            else:
                self.log_test("Session Config", False, f"Status: {response.status_code}")
            
            return True
            
        except Exception as e:
            self.log_test("Session API", False, f"Exception: {str(e)}")
            return False
    
    def test_matches_api(self):
        """Test match-related endpoints"""
        try:
            # Test GET matches
            response = self.session.get(f"{self.base_url}/matches")
            if response.status_code != 200:
                self.log_test("Matches GET", False, f"Status: {response.status_code}", response.text)
                return False
            
            matches = response.json()
            self.log_test("Matches GET", True, f"Retrieved {len(matches)} matches")
            
            # Test current round matches
            response = self.session.get(f"{self.base_url}/matches/current")
            if response.status_code == 200:
                current_matches = response.json()
                self.log_test("Current Matches", True, f"Current round has {len(current_matches)} matches")
            else:
                self.log_test("Current Matches", False, f"Status: {response.status_code}")
            
            return True
            
        except Exception as e:
            self.log_test("Matches API", False, f"Exception: {str(e)}")
            return False
    
    def test_match_generation(self):
        """Test match generation functionality"""
        try:
            # First ensure we have enough active players
            response = self.session.get(f"{self.base_url}/players")
            if response.status_code != 200:
                self.log_test("Match Generation - Get Players", False, f"Cannot get players: {response.status_code}")
                return False
            
            players = response.json()
            active_players = [p for p in players if p.get("isActive", False)]
            
            if len(active_players) < 4:
                self.log_test("Match Generation - Player Count", False, f"Need at least 4 active players, found {len(active_players)}")
                return False
            
            self.log_test("Match Generation - Player Count", True, f"Found {len(active_players)} active players")
            
            # Test generate matches
            response = self.session.post(f"{self.base_url}/session/generate-matches")
            if response.status_code != 200:
                self.log_test("Match Generation - Generate", False, f"Status: {response.status_code}", response.text)
                return False
            
            generation_result = response.json()
            generated_matches = generation_result.get("matches", [])
            self.log_test("Match Generation - Generate", True, f"Generated {len(generated_matches)} matches")
            
            # Verify matches have proper structure
            if generated_matches:
                sample_match = generated_matches[0]
                required_fields = ["id", "teamA", "teamB", "category", "matchType", "status"]
                missing_fields = [field for field in required_fields if field not in sample_match]
                
                if not missing_fields:
                    self.log_test("Match Generation - Structure", True, "Generated matches have correct structure")
                else:
                    self.log_test("Match Generation - Structure", False, f"Missing fields: {missing_fields}")
            
            return True
            
        except Exception as e:
            self.log_test("Match Generation", False, f"Exception: {str(e)}")
            return False
    
    def test_database_operations(self):
        """Test database-related operations"""
        try:
            # Test add test data
            response = self.session.post(f"{self.base_url}/add-test-data")
            if response.status_code != 200:
                self.log_test("Database - Add Test Data", False, f"Status: {response.status_code}", response.text)
                return False
            
            result = response.json()
            self.log_test("Database - Add Test Data", True, result.get("message", "Test data added"))
            
            # Verify test data was added
            response = self.session.get(f"{self.base_url}/players")
            if response.status_code == 200:
                players = response.json()
                test_players_count = len([p for p in players if "Test" not in p.get("name", "")])
                self.log_test("Database - Verify Test Data", True, f"Found {len(players)} total players after adding test data")
            
            return True
            
        except Exception as e:
            self.log_test("Database Operations", False, f"Exception: {str(e)}")
            return False
    
    def test_clubs_api(self):
        """Test clubs API endpoints"""
        try:
            # Test GET clubs
            response = self.session.get(f"{self.base_url}/clubs")
            if response.status_code != 200:
                self.log_test("Clubs GET", False, f"Status: {response.status_code}", response.text)
                return False
            
            clubs = response.json()
            self.log_test("Clubs GET", True, f"Retrieved {len(clubs)} clubs")
            
            # Verify Main Club exists
            main_club = next((c for c in clubs if c["name"] == "Main Club"), None)
            if main_club:
                self.log_test("Clubs - Main Club", True, "Main Club exists")
            else:
                self.log_test("Clubs - Main Club", False, "Main Club not found")
            
            return True
            
        except Exception as e:
            self.log_test("Clubs API", False, f"Exception: {str(e)}")
            return False
    
    def test_club_authentication(self):
        """Test club authentication system"""
        try:
            # Test 1: Club login with correct credentials
            login_data = {
                "club_name": "Main Club",
                "access_code": "demo123"
            }
            
            response = self.session.post(f"{self.base_url}/auth/login", json=login_data)
            if response.status_code == 200:
                login_response = response.json()
                expected_fields = ["club_name", "display_name", "authenticated"]
                missing_fields = [field for field in expected_fields if field not in login_response]
                
                if not missing_fields and login_response.get("authenticated") == True:
                    self.log_test("Auth - Login Correct Credentials", True, "Login successful with correct response format")
                else:
                    self.log_test("Auth - Login Correct Credentials", False, f"Response format incorrect. Missing: {missing_fields}")
            else:
                self.log_test("Auth - Login Correct Credentials", False, f"Status: {response.status_code}", response.text)
            
            # Test 2: Club login with wrong club name
            wrong_club_data = {
                "club_name": "NonExistent Club",
                "access_code": "demo123"
            }
            
            response = self.session.post(f"{self.base_url}/auth/login", json=wrong_club_data)
            if response.status_code == 404:
                self.log_test("Auth - Login Wrong Club Name", True, "Correctly rejected non-existent club")
            else:
                self.log_test("Auth - Login Wrong Club Name", False, f"Expected 404, got {response.status_code}")
            
            # Test 3: Club login with wrong access code
            wrong_code_data = {
                "club_name": "Main Club",
                "access_code": "wrongcode"
            }
            
            response = self.session.post(f"{self.base_url}/auth/login", json=wrong_code_data)
            if response.status_code == 401:
                self.log_test("Auth - Login Wrong Access Code", True, "Correctly rejected wrong access code")
            else:
                self.log_test("Auth - Login Wrong Access Code", False, f"Expected 401, got {response.status_code}")
            
            # Test 4: Club registration with new club
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            new_club_data = {
                "name": f"Test Club {unique_id}",
                "display_name": f"Test Club {unique_id}",
                "description": "Test club for authentication testing",
                "access_code": f"test{unique_id}"
            }
            
            response = self.session.post(f"{self.base_url}/auth/register", json=new_club_data)
            if response.status_code == 200:
                register_response = response.json()
                expected_fields = ["club_name", "display_name", "authenticated"]
                missing_fields = [field for field in expected_fields if field not in register_response]
                
                if not missing_fields and register_response.get("authenticated") == True:
                    self.log_test("Auth - Register New Club", True, "Club registration successful")
                    # Store for later tests
                    self.test_club_name = new_club_data["name"]
                    self.test_club_access_code = new_club_data["access_code"]
                else:
                    self.log_test("Auth - Register New Club", False, f"Response format incorrect. Missing: {missing_fields}")
            else:
                self.log_test("Auth - Register New Club", False, f"Status: {response.status_code}", response.text)
            
            # Test 5: Club registration with duplicate name
            duplicate_club_data = {
                "name": "Main Club",
                "display_name": "Duplicate Main Club",
                "description": "This should fail",
                "access_code": "duplicate123"
            }
            
            response = self.session.post(f"{self.base_url}/auth/register", json=duplicate_club_data)
            if response.status_code == 400:
                self.log_test("Auth - Register Duplicate Name", True, "Correctly rejected duplicate club name")
            else:
                self.log_test("Auth - Register Duplicate Name", False, f"Expected 400, got {response.status_code}")
            
            # Test 6: Club registration with missing fields
            incomplete_club_data = {
                "name": "Incomplete Club",
                "display_name": "Incomplete Club"
                # Missing access_code
            }
            
            response = self.session.post(f"{self.base_url}/auth/register", json=incomplete_club_data)
            if response.status_code >= 400:
                self.log_test("Auth - Register Missing Fields", True, "Correctly rejected incomplete data")
            else:
                self.log_test("Auth - Register Missing Fields", False, f"Expected error status, got {response.status_code}")
            
            return True
            
        except Exception as e:
            self.log_test("Club Authentication", False, f"Exception: {str(e)}")
            return False
    
    def test_club_aware_endpoints(self):
        """Test club-aware player endpoints"""
        try:
            # Test 1: Players endpoint with club_name parameter
            params = {"club_name": "Main Club"}
            response = self.session.get(f"{self.base_url}/players", params=params)
            
            if response.status_code == 200:
                players = response.json()
                if isinstance(players, list):
                    self.log_test("Club-Aware - Players GET", True, f"Retrieved {len(players)} players for Main Club")
                    
                    # Verify player structure
                    if players:
                        player = players[0]
                        required_fields = ["id", "name", "category", "isActive"]
                        missing_fields = [field for field in required_fields if field not in player]
                        
                        if not missing_fields:
                            self.log_test("Club-Aware - Player Structure", True, "Players have correct structure")
                        else:
                            self.log_test("Club-Aware - Player Structure", False, f"Missing fields: {missing_fields}")
                else:
                    self.log_test("Club-Aware - Players GET", False, "Response should be a list of players")
            else:
                self.log_test("Club-Aware - Players GET", False, f"Status: {response.status_code}", response.text)
            
            # Test 2: Player creation with club_name parameter
            test_player_data = {
                "name": "Test Player Auth",
                "category": "Beginner"
            }
            
            params = {"club_name": "Main Club"}
            response = self.session.post(f"{self.base_url}/players", json=test_player_data, params=params)
            
            if response.status_code == 200:
                created_player = response.json()
                required_fields = ["id", "name", "category", "isActive"]
                missing_fields = [field for field in required_fields if field not in created_player]
                
                if not missing_fields:
                    self.log_test("Club-Aware - Player Creation", True, f"Created player: {created_player['name']}")
                    self.created_players.append(created_player["id"])  # For cleanup
                    
                    # Test 3: Player toggle with club_name parameter
                    params = {"club_name": "Main Club"}
                    response = self.session.patch(f"{self.base_url}/players/{created_player['id']}/toggle-active", params=params)
                    
                    if response.status_code == 200:
                        toggle_response = response.json()
                        if "message" in toggle_response and "isActive" in toggle_response:
                            self.log_test("Club-Aware - Player Toggle", True, "Player toggle successful")
                        else:
                            self.log_test("Club-Aware - Player Toggle", False, "Response missing required fields")
                    else:
                        self.log_test("Club-Aware - Player Toggle", False, f"Status: {response.status_code}", response.text)
                else:
                    self.log_test("Club-Aware - Player Creation", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("Club-Aware - Player Creation", False, f"Status: {response.status_code}", response.text)
            
            return True
            
        except Exception as e:
            self.log_test("Club-Aware Endpoints", False, f"Exception: {str(e)}")
            return False
    
    def test_database_schema_verification(self):
        """Test database schema for club authentication"""
        try:
            # Test that clubs table exists and has access_code field by testing login
            # (access_code field is not returned in GET /clubs for security)
            
            # Test 1: Verify Main Club exists with demo123 access code
            login_data = {
                "club_name": "Main Club",
                "access_code": "demo123"
            }
            
            response = self.session.post(f"{self.base_url}/auth/login", json=login_data)
            if response.status_code == 200:
                self.log_test("DB Schema - Main Club Access Code", True, "Main Club exists with demo123 access code")
            else:
                self.log_test("DB Schema - Main Club Access Code", False, f"Main Club login failed: {response.status_code}")
            
            # Test 2: Verify clubs table structure via GET endpoint
            response = self.session.get(f"{self.base_url}/clubs")
            if response.status_code == 200:
                clubs = response.json()
                if clubs:
                    club = clubs[0]
                    required_fields = ["name", "display_name"]
                    missing_fields = [field for field in required_fields if field not in club]
                    
                    if not missing_fields:
                        self.log_test("DB Schema - Clubs Table Structure", True, "Clubs table has correct structure")
                    else:
                        self.log_test("DB Schema - Clubs Table Structure", False, f"Missing fields: {missing_fields}")
                else:
                    self.log_test("DB Schema - Clubs Table Structure", False, "No clubs found in database")
            else:
                self.log_test("DB Schema - Clubs Table Structure", False, f"Cannot access clubs: {response.status_code}")
            
            # Test 3: Verify session table has club-specific data
            response = self.session.get(f"{self.base_url}/session")
            if response.status_code == 200:
                session_data = response.json()
                if session_data:
                    self.log_test("DB Schema - Session Club Data", True, "Session data accessible (club-specific)")
                else:
                    self.log_test("DB Schema - Session Club Data", False, "No session data found")
            else:
                self.log_test("DB Schema - Session Club Data", False, f"Cannot access session: {response.status_code}")
            
            return True
            
        except Exception as e:
            self.log_test("Database Schema Verification", False, f"Exception: {str(e)}")
            return False
    
    def cleanup_test_data(self):
        """Clean up test data created during testing"""
        try:
            # Delete test players
            for player_id in self.created_players:
                response = self.session.delete(f"{self.base_url}/players/{player_id}")
                if response.status_code == 200:
                    print(f"✅ Cleaned up test player: {player_id}")
                else:
                    print(f"⚠️  Failed to clean up test player: {player_id}")
            
            # Delete test categories
            for category_id in self.created_categories:
                response = self.session.delete(f"{self.base_url}/categories/{category_id}")
                if response.status_code == 200:
                    print(f"✅ Cleaned up test category: {category_id}")
                else:
                    print(f"⚠️  Failed to clean up test category: {category_id}")
                    
        except Exception as e:
            print(f"⚠️  Error during cleanup: {str(e)}")
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting CourtChime Backend API Tests")
        print(f"🔗 Testing backend at: {self.base_url}")
        print("=" * 60)
        
        # Core connectivity test
        if not self.test_health_check():
            print("❌ Backend is not accessible. Stopping tests.")
            return False
        
        # Test all API endpoints
        self.test_clubs_api()
        self.test_categories_api()
        
        # Test players API with focus on isActive functionality
        created_player = self.test_players_api()
        
        # Test the critical toggle-active endpoint
        if created_player:
            self.test_player_toggle_active(created_player["id"])
        else:
            # Try with existing players if any
            response = self.session.get(f"{self.base_url}/players")
            if response.status_code == 200:
                players = response.json()
                if players:
                    self.test_player_toggle_active(players[0]["id"])
        
        # Test other core functionality
        self.test_session_api()
        self.test_matches_api()
        self.test_database_operations()
        self.test_match_generation()
        
        # Clean up test data
        self.cleanup_test_data()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        failed = len(self.test_results) - passed
        
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {(passed/len(self.test_results)*100):.1f}%")
        
        if failed > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   ❌ {result['test']}: {result['message']}")
        
        return failed == 0

def main():
    """Main test execution"""
    tester = CourtChimeAPITester(BACKEND_URL)
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! Backend is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Check the details above.")
        sys.exit(1)

if __name__ == "__main__":
    main()