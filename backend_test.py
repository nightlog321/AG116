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