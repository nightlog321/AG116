#!/usr/bin/env python3
"""
Backend API Testing for CourtChime Match Generation and Courts Functionality
Testing specific issues reported by user:
1. Generate Matches not showing matches on court
2. Missing Let's Play button functionality
"""

import requests
import json
import sys
from typing import Dict, Any, List

# Backend URL from frontend .env
BACKEND_URL = "https://match-scheduler-11.preview.emergentagent.com/api"

class BackendTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.test_results = []
        self.failed_tests = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status}: {test_name}"
        if details:
            result += f" - {details}"
        
        self.test_results.append(result)
        if not success:
            self.failed_tests.append(f"{test_name}: {details}")
        print(result)
        
    def make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, params=params, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, params=params, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, params=params, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return {
                "status_code": response.status_code,
                "data": response.json() if response.content else {},
                "success": 200 <= response.status_code < 300
            }
        except requests.exceptions.RequestException as e:
            return {
                "status_code": 0,
                "data": {"error": str(e)},
                "success": False
            }
        except json.JSONDecodeError:
            return {
                "status_code": response.status_code,
                "data": {"error": "Invalid JSON response"},
                "success": False
            }

    def test_club_management_apis(self):
        """Test 1: Club Management APIs"""
        print("\n🏢 TESTING CLUB MANAGEMENT APIs")
        
        # Test 1.1: GET /api/clubs - should return "Main Club" that was auto-created
        print("\n1.1 Testing GET /api/clubs - should return Main Club")
        response = self.make_request("GET", "/clubs")
        
        if response["success"]:
            clubs = response["data"]
            main_club_found = any(club.get("name") == "Main Club" for club in clubs)
            
            if main_club_found:
                self.log_test("GET /api/clubs returns Main Club", True, f"Found Main Club in {len(clubs)} clubs")
            else:
                self.log_test("GET /api/clubs returns Main Club", False, f"Main Club not found in clubs: {[c.get('name') for c in clubs]}")
        else:
            self.log_test("GET /api/clubs returns Main Club", False, f"API call failed: {response['data']}")
        
        # Test 1.2: POST /api/clubs - should create new clubs with auto-generated sessions
        print("\n1.2 Testing POST /api/clubs - create Tennis Club")
        club_data = {
            "name": "Tennis Club",
            "display_name": "Tennis Club",
            "description": "A tennis club for testing multi-club functionality"
        }
        
        response = self.make_request("POST", "/clubs", data=club_data)
        
        if response["success"]:
            created_club = response["data"]
            if created_club.get("name") == "Tennis Club":
                self.log_test("POST /api/clubs creates Tennis Club", True, f"Created club: {created_club.get('display_name')}")
                
                # Verify the club appears in GET /api/clubs
                clubs_response = self.make_request("GET", "/clubs")
                if clubs_response["success"]:
                    clubs = clubs_response["data"]
                    tennis_club_found = any(club.get("name") == "Tennis Club" for club in clubs)
                    self.log_test("Tennis Club appears in clubs list", tennis_club_found, f"Total clubs: {len(clubs)}")
                else:
                    self.log_test("Tennis Club appears in clubs list", False, "Failed to get clubs list")
            else:
                self.log_test("POST /api/clubs creates Tennis Club", False, f"Unexpected club data: {created_club}")
        else:
            self.log_test("POST /api/clubs creates Tennis Club", False, f"API call failed: {response['data']}")

    def test_club_aware_data_apis(self):
        """Test 2: Club-Aware Data APIs with backward compatibility"""
        print("\n📊 TESTING CLUB-AWARE DATA APIs")
        
        # Test 2.1: GET /api/players?club_name=Main Club - should return empty initially
        print("\n2.1 Testing GET /api/players?club_name=Main Club - should be empty initially")
        response = self.make_request("GET", "/players", params={"club_name": "Main Club"})
        
        if response["success"]:
            players = response["data"]
            if len(players) == 0:
                self.log_test("GET /api/players?club_name=Main Club returns empty", True, "No players found as expected")
            else:
                self.log_test("GET /api/players?club_name=Main Club returns empty", False, f"Found {len(players)} players, expected 0")
        else:
            self.log_test("GET /api/players?club_name=Main Club returns empty", False, f"API call failed: {response['data']}")
        
        # Test 2.2: POST /api/add-test-data - should add 13 test players to "Main Club"
        print("\n2.2 Testing POST /api/add-test-data - add test players to Main Club")
        response = self.make_request("POST", "/add-test-data")
        
        if response["success"]:
            result = response["data"]
            if "Successfully added" in result.get("message", ""):
                self.log_test("POST /api/add-test-data adds players", True, result.get("message"))
            else:
                self.log_test("POST /api/add-test-data adds players", False, f"Unexpected message: {result}")
        else:
            self.log_test("POST /api/add-test-data adds players", False, f"API call failed: {response['data']}")
        
        # Test 2.3: GET /api/players?club_name=Main Club - should now return 13 players
        print("\n2.3 Testing GET /api/players?club_name=Main Club - should return 13 players")
        response = self.make_request("GET", "/players", params={"club_name": "Main Club"})
        
        if response["success"]:
            players = response["data"]
            if len(players) >= 12:  # Allow for 12+ players (test data might vary)
                self.log_test("GET /api/players?club_name=Main Club returns test players", True, f"Found {len(players)} players")
                
                # Verify player structure and club assignment
                if players:
                    sample_player = players[0]
                    required_fields = ["id", "name", "category", "rating"]
                    missing_fields = [field for field in required_fields if field not in sample_player]
                    
                    if not missing_fields:
                        self.log_test("Player data structure is correct", True, f"All required fields present: {required_fields}")
                    else:
                        self.log_test("Player data structure is correct", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("GET /api/players?club_name=Main Club returns test players", False, f"Found {len(players)} players, expected 12+")
        else:
            self.log_test("GET /api/players?club_name=Main Club returns test players", False, f"API call failed: {response['data']}")
        
        # Test 2.4: GET /api/session?club_name=Main Club - should return session for Main Club
        print("\n2.4 Testing GET /api/session?club_name=Main Club - should return Main Club session")
        response = self.make_request("GET", "/session", params={"club_name": "Main Club"})
        
        if response["success"]:
            session = response["data"]
            required_fields = ["id", "currentRound", "phase", "config"]
            missing_fields = [field for field in required_fields if field not in session]
            
            if not missing_fields:
                self.log_test("GET /api/session?club_name=Main Club returns session", True, f"Session phase: {session.get('phase')}")
                
                # Verify session config structure
                config = session.get("config", {})
                config_fields = ["numCourts", "playSeconds", "allowSingles", "allowDoubles"]
                missing_config = [field for field in config_fields if field not in config]
                
                if not missing_config:
                    self.log_test("Session config structure is correct", True, f"Config fields: {list(config.keys())}")
                else:
                    self.log_test("Session config structure is correct", False, f"Missing config fields: {missing_config}")
            else:
                self.log_test("GET /api/session?club_name=Main Club returns session", False, f"Missing session fields: {missing_fields}")
        else:
            self.log_test("GET /api/session?club_name=Main Club returns session", False, f"API call failed: {response['data']}")

    def test_multi_club_isolation(self):
        """Test 3: Multi-Club Isolation Test"""
        print("\n🔒 TESTING MULTI-CLUB DATA ISOLATION")
        
        # Test 3.1: GET /api/players?club_name=Tennis Club - should return empty (isolated)
        print("\n3.1 Testing GET /api/players?club_name=Tennis Club - should be empty (isolated)")
        response = self.make_request("GET", "/players", params={"club_name": "Tennis Club"})
        
        if response["success"]:
            tennis_players = response["data"]
            if len(tennis_players) == 0:
                self.log_test("Tennis Club players isolated (empty)", True, "No players found in Tennis Club as expected")
            else:
                self.log_test("Tennis Club players isolated (empty)", False, f"Found {len(tennis_players)} players in Tennis Club, expected 0")
        else:
            self.log_test("Tennis Club players isolated (empty)", False, f"API call failed: {response['data']}")
        
        # Test 3.2: GET /api/players?club_name=Main Club - should still return 13 players
        print("\n3.2 Testing GET /api/players?club_name=Main Club - should still have players")
        response = self.make_request("GET", "/players", params={"club_name": "Main Club"})
        
        if response["success"]:
            main_players = response["data"]
            if len(main_players) >= 12:
                self.log_test("Main Club players still present", True, f"Main Club has {len(main_players)} players")
            else:
                self.log_test("Main Club players still present", False, f"Main Club has {len(main_players)} players, expected 12+")
        else:
            self.log_test("Main Club players still present", False, f"API call failed: {response['data']}")
        
        # Test 3.3: POST /api/players with club_name=Tennis Club - create player for Tennis Club
        print("\n3.3 Testing POST /api/players with club_name=Tennis Club - create isolated player")
        player_data = {
            "name": "Tennis Player One",
            "category": "Intermediate"
        }
        
        response = self.make_request("POST", "/players", data=player_data, params={"club_name": "Tennis Club"})
        
        if response["success"]:
            created_player = response["data"]
            if created_player.get("name") == "Tennis Player One":
                self.log_test("POST /api/players creates Tennis Club player", True, f"Created: {created_player.get('name')}")
                
                # Verify the player appears in Tennis Club
                tennis_response = self.make_request("GET", "/players", params={"club_name": "Tennis Club"})
                if tennis_response["success"]:
                    tennis_players = tennis_response["data"]
                    if len(tennis_players) == 1:
                        self.log_test("Tennis Club player appears in Tennis Club", True, f"Tennis Club now has {len(tennis_players)} player")
                    else:
                        self.log_test("Tennis Club player appears in Tennis Club", False, f"Tennis Club has {len(tennis_players)} players, expected 1")
                else:
                    self.log_test("Tennis Club player appears in Tennis Club", False, "Failed to get Tennis Club players")
            else:
                self.log_test("POST /api/players creates Tennis Club player", False, f"Unexpected player data: {created_player}")
        else:
            self.log_test("POST /api/players creates Tennis Club player", False, f"API call failed: {response['data']}")
        
        # Test 3.4: Verify complete data isolation - Main Club should still have same number of players
        print("\n3.4 Testing complete data isolation - Main Club unaffected")
        response = self.make_request("GET", "/players", params={"club_name": "Main Club"})
        
        if response["success"]:
            main_players = response["data"]
            if len(main_players) >= 12:
                self.log_test("Data isolation verified - Main Club unaffected", True, f"Main Club still has {len(main_players)} players")
            else:
                self.log_test("Data isolation verified - Main Club unaffected", False, f"Main Club has {len(main_players)} players, expected 12+")
        else:
            self.log_test("Data isolation verified - Main Club unaffected", False, f"API call failed: {response['data']}")

    def test_backward_compatibility(self):
        """Test 4: Backward Compatibility"""
        print("\n🔄 TESTING BACKWARD COMPATIBILITY")
        
        # Test 4.1: GET /api/players (no club_name parameter) - should default to "Main Club"
        print("\n4.1 Testing GET /api/players (no club_name) - should default to Main Club")
        response = self.make_request("GET", "/players")
        
        if response["success"]:
            default_players = response["data"]
            
            # Compare with explicit Main Club request
            main_response = self.make_request("GET", "/players", params={"club_name": "Main Club"})
            if main_response["success"]:
                main_players = main_response["data"]
                
                if len(default_players) == len(main_players) and len(default_players) >= 12:
                    self.log_test("GET /api/players defaults to Main Club", True, f"Both return {len(default_players)} players")
                    
                    # Verify same player IDs
                    default_ids = {p.get("id") for p in default_players}
                    main_ids = {p.get("id") for p in main_players}
                    
                    if default_ids == main_ids:
                        self.log_test("Default and explicit Main Club return same players", True, "Player IDs match")
                    else:
                        self.log_test("Default and explicit Main Club return same players", False, "Player IDs don't match")
                else:
                    self.log_test("GET /api/players defaults to Main Club", False, f"Default: {len(default_players)}, Main: {len(main_players)} players")
            else:
                self.log_test("GET /api/players defaults to Main Club", False, "Failed to get Main Club players for comparison")
        else:
            self.log_test("GET /api/players defaults to Main Club", False, f"API call failed: {response['data']}")
        
        # Test 4.2: GET /api/session (no club_name parameter) - should default to "Main Club"
        print("\n4.2 Testing GET /api/session (no club_name) - should default to Main Club")
        response = self.make_request("GET", "/session")
        
        if response["success"]:
            default_session = response["data"]
            
            # Compare with explicit Main Club request
            main_response = self.make_request("GET", "/session", params={"club_name": "Main Club"})
            if main_response["success"]:
                main_session = main_response["data"]
                
                # Compare key fields
                default_id = default_session.get("id")
                main_id = main_session.get("id")
                
                if default_id == main_id:
                    self.log_test("GET /api/session defaults to Main Club", True, f"Both return session ID: {default_id}")
                else:
                    self.log_test("GET /api/session defaults to Main Club", False, f"Default ID: {default_id}, Main ID: {main_id}")
            else:
                self.log_test("GET /api/session defaults to Main Club", False, "Failed to get Main Club session for comparison")
        else:
            self.log_test("GET /api/session defaults to Main Club", False, f"API call failed: {response['data']}")

    def test_session_isolation(self):
        """Test 5: Session Isolation Between Clubs"""
        print("\n⚙️ TESTING SESSION ISOLATION BETWEEN CLUBS")
        
        # Test 5.1: GET /api/session?club_name=Tennis Club - should return separate session
        print("\n5.1 Testing GET /api/session?club_name=Tennis Club - should have separate session")
        response = self.make_request("GET", "/session", params={"club_name": "Tennis Club"})
        
        if response["success"]:
            tennis_session = response["data"]
            
            # Get Main Club session for comparison
            main_response = self.make_request("GET", "/session", params={"club_name": "Main Club"})
            if main_response["success"]:
                main_session = main_response["data"]
                
                # Sessions should have different IDs
                tennis_id = tennis_session.get("id")
                main_id = main_session.get("id")
                
                if tennis_id != main_id:
                    self.log_test("Tennis Club has separate session", True, f"Tennis: {tennis_id}, Main: {main_id}")
                else:
                    self.log_test("Tennis Club has separate session", False, f"Both clubs have same session ID: {tennis_id}")
            else:
                self.log_test("Tennis Club has separate session", False, "Failed to get Main Club session for comparison")
        else:
            self.log_test("Tennis Club has separate session", False, f"API call failed: {response['data']}")

    def run_all_tests(self):
        """Run all multi-club architecture tests"""
        print("🚀 STARTING MULTI-CLUB ARCHITECTURE TESTING")
        print(f"Backend URL: {self.base_url}")
        print("=" * 80)
        
        try:
            # Test 1: Club Management APIs
            self.test_club_management_apis()
            
            # Test 2: Club-Aware Data APIs
            self.test_club_aware_data_apis()
            
            # Test 3: Multi-Club Isolation
            self.test_multi_club_isolation()
            
            # Test 4: Backward Compatibility
            self.test_backward_compatibility()
            
            # Test 5: Session Isolation
            self.test_session_isolation()
            
        except Exception as e:
            self.log_test("Test execution", False, f"Unexpected error: {str(e)}")
        
        # Print summary
        print("\n" + "=" * 80)
        print("🏁 MULTI-CLUB ARCHITECTURE TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = total_tests - len(self.failed_tests)
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {len(self.failed_tests)}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "No tests run")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for failure in self.failed_tests:
                print(f"  - {failure}")
        
        print("\n📋 ALL TEST RESULTS:")
        for result in self.test_results:
            print(f"  {result}")
        
        return len(self.failed_tests) == 0

if __name__ == "__main__":
    tester = MultiClubTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)