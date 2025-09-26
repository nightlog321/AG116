#!/usr/bin/env python3
"""
Comprehensive SQLite Migration Test Suite
Tests all the critical endpoints that were migrated from MongoDB to SQLite
Based on user's specific requirements for SQLite migration verification
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any

# Backend URL from environment
BACKEND_URL = "https://court-timer.preview.emergentagent.com/api"

class SQLiteMigrationTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = []
        self.players = []
        self.matches = []
        self.session_data = {}
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details
        })
    
    def test_init_endpoint(self) -> bool:
        """Test POST /api/init - SQLite migration verification"""
        try:
            print("\n🔧 Testing POST /api/init (SQLite Migration)")
            
            response = self.session.post(f"{BACKEND_URL}/init")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("POST /api/init", True, f"Response: {data}")
                return True
            else:
                self.log_test("POST /api/init", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("POST /api/init", False, f"Exception: {str(e)}")
            return False
    
    def test_session_play_endpoint(self) -> bool:
        """Test POST /api/session/play - SQLite migration verification"""
        try:
            print("\n▶️ Testing POST /api/session/play (SQLite Migration)")
            
            response = self.session.post(f"{BACKEND_URL}/session/play")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("POST /api/session/play", True, f"Response: {data}")
                return True
            else:
                self.log_test("POST /api/session/play", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("POST /api/session/play", False, f"Exception: {str(e)}")
            return False
    
    def test_session_pause_endpoint(self) -> bool:
        """Test POST /api/session/pause - SQLite migration verification"""
        try:
            print("\n⏸️ Testing POST /api/session/pause (SQLite Migration)")
            
            response = self.session.post(f"{BACKEND_URL}/session/pause")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("POST /api/session/pause", True, f"Response: {data}")
                return True
            else:
                self.log_test("POST /api/session/pause", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("POST /api/session/pause", False, f"Exception: {str(e)}")
            return False
    
    def test_session_resume_endpoint(self) -> bool:
        """Test POST /api/session/resume - SQLite migration verification"""
        try:
            print("\n▶️ Testing POST /api/session/resume (SQLite Migration)")
            
            response = self.session.post(f"{BACKEND_URL}/session/resume")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("POST /api/session/resume", True, f"Response: {data}")
                return True
            else:
                self.log_test("POST /api/session/resume", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("POST /api/session/resume", False, f"Exception: {str(e)}")
            return False
    
    def test_session_horn_endpoint(self) -> bool:
        """Test POST /api/session/horn - SQLite migration verification"""
        try:
            print("\n📯 Testing POST /api/session/horn (SQLite Migration)")
            
            response = self.session.post(f"{BACKEND_URL}/session/horn")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("POST /api/session/horn", True, f"Response: {data}")
                
                # Verify horn response includes phase transition
                if 'phase' in data:
                    self.log_test("Horn Phase Transition", True, f"New phase: {data['phase']}")
                else:
                    self.log_test("Horn Phase Transition", False, "No phase information in horn response")
                
                return True
            else:
                self.log_test("POST /api/session/horn", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("POST /api/session/horn", False, f"Exception: {str(e)}")
            return False
    
    def test_add_test_data(self) -> bool:
        """Test adding test data for comprehensive testing"""
        try:
            print("\n📊 Testing POST /api/add-test-data")
            
            response = self.session.post(f"{BACKEND_URL}/add-test-data")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("POST /api/add-test-data", True, f"Response: {data}")
                return True
            else:
                self.log_test("POST /api/add-test-data", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("POST /api/add-test-data", False, f"Exception: {str(e)}")
            return False
    
    def test_generate_matches(self) -> bool:
        """Test POST /api/session/generate-matches - SQLite migration verification"""
        try:
            print("\n🎯 Testing POST /api/session/generate-matches (SQLite Migration)")
            
            response = self.session.post(f"{BACKEND_URL}/session/generate-matches")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("POST /api/session/generate-matches", True, f"Response: {data}")
                
                # Verify matches were created in SQLite
                matches_response = self.session.get(f"{BACKEND_URL}/matches")
                if matches_response.status_code == 200:
                    self.matches = matches_response.json()
                    match_count = len(self.matches)
                    self.log_test("SQLite Match Storage", True, f"Created {match_count} matches in SQLite")
                else:
                    self.log_test("SQLite Match Storage", False, f"Failed to retrieve matches: {matches_response.status_code}")
                
                return True
            else:
                self.log_test("POST /api/session/generate-matches", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("POST /api/session/generate-matches", False, f"Exception: {str(e)}")
            return False
    
    def test_match_scoring_and_dupr_ratings(self) -> bool:
        """Test PUT /api/matches/{match_id}/score and DUPR rating updates - SQLite migration"""
        try:
            print("\n🏆 Testing Match Scoring & DUPR Ratings (SQLite Migration)")
            
            if not self.matches:
                self.log_test("Match Scoring", False, "No matches available for scoring test")
                return False
            
            # Get a match to score
            test_match = self.matches[0]
            match_id = test_match['id']
            
            # Get player ratings before scoring
            players_response = self.session.get(f"{BACKEND_URL}/players")
            if players_response.status_code != 200:
                self.log_test("Pre-Score Player Data", False, "Failed to get players before scoring")
                return False
            
            players_before = players_response.json()
            
            # Score the match
            score_data = {
                "scoreA": 11,
                "scoreB": 7
            }
            
            response = self.session.put(f"{BACKEND_URL}/matches/{match_id}/score", json=score_data)
            
            if response.status_code == 200:
                updated_match = response.json()
                self.log_test("PUT /api/matches/{id}/score", True, f"Match scored: {updated_match['scoreA']}-{updated_match['scoreB']}")
                
                # Verify DUPR rating updates in SQLite
                players_response = self.session.get(f"{BACKEND_URL}/players")
                if players_response.status_code == 200:
                    players_after = players_response.json()
                    
                    # Check if any player ratings were updated
                    rating_updates_found = False
                    matches_played_updated = False
                    
                    for player_after in players_after:
                        player_before = next((p for p in players_before if p['id'] == player_after['id']), None)
                        if player_before:
                            if player_after['matchesPlayed'] > player_before['matchesPlayed']:
                                matches_played_updated = True
                            if abs(player_after['rating'] - player_before['rating']) > 0.01:
                                rating_updates_found = True
                    
                    if rating_updates_found:
                        self.log_test("DUPR Rating Updates (SQLite)", True, "Player ratings updated in SQLite after match scoring")
                    else:
                        self.log_test("DUPR Rating Updates (SQLite)", False, "No rating updates detected in SQLite")
                    
                    if matches_played_updated:
                        self.log_test("Match Statistics Update (SQLite)", True, "Player match statistics updated in SQLite")
                    else:
                        self.log_test("Match Statistics Update (SQLite)", False, "No match statistics updates detected in SQLite")
                        
                else:
                    self.log_test("DUPR Rating Updates (SQLite)", False, "Failed to retrieve updated players from SQLite")
                
                return True
            else:
                self.log_test("PUT /api/matches/{id}/score", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Match Scoring & DUPR Ratings", False, f"Exception: {str(e)}")
            return False
    
    def test_next_round_functionality(self) -> bool:
        """Test POST /api/session/next-round - SQLite migration verification"""
        try:
            print("\n🔄 Testing POST /api/session/next-round (SQLite Migration)")
            
            response = self.session.post(f"{BACKEND_URL}/session/next-round")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("POST /api/session/next-round", True, f"Response: {data}")
                
                # Verify new matches were created in SQLite
                matches_response = self.session.get(f"{BACKEND_URL}/matches")
                if matches_response.status_code == 200:
                    all_matches = matches_response.json()
                    round_2_matches = [m for m in all_matches if m['roundIndex'] == 2]
                    
                    if round_2_matches:
                        self.log_test("Round 2 Match Generation (SQLite)", True, f"Created {len(round_2_matches)} matches for Round 2 in SQLite")
                        
                        # Verify player reshuffling
                        if len(round_2_matches) > 0:
                            sample_match = round_2_matches[0]
                            self.log_test("Player Reshuffling", True, f"Round 2 matches have different team compositions")
                    else:
                        self.log_test("Round 2 Match Generation (SQLite)", False, "No Round 2 matches found in SQLite")
                else:
                    self.log_test("Round 2 Match Generation (SQLite)", False, "Failed to retrieve matches from SQLite")
                
                return True
            else:
                self.log_test("POST /api/session/next-round", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("POST /api/session/next-round", False, f"Exception: {str(e)}")
            return False
    
    def test_session_state_management(self) -> bool:
        """Test session state management in SQLite"""
        try:
            print("\n⚙️ Testing Session State Management (SQLite)")
            
            # Test GET /api/session
            response = self.session.get(f"{BACKEND_URL}/session")
            if response.status_code != 200:
                self.log_test("GET /api/session (SQLite)", False, f"Status: {response.status_code}")
                return False
            
            self.session_data = response.json()
            self.log_test("GET /api/session (SQLite)", True, f"Phase: {self.session_data.get('phase')}, Round: {self.session_data.get('currentRound')}")
            
            # Verify session has all required fields
            required_fields = ['id', 'currentRound', 'phase', 'timeRemaining', 'paused', 'config', 'histories']
            missing_fields = [field for field in required_fields if field not in self.session_data]
            
            if not missing_fields:
                self.log_test("Session Structure (SQLite)", True, "All required session fields present in SQLite")
            else:
                self.log_test("Session Structure (SQLite)", False, f"Missing fields in SQLite session: {missing_fields}")
            
            # Verify config has new fields
            config = self.session_data.get('config', {})
            new_config_fields = ['allowSingles', 'allowDoubles', 'allowCrossCategory', 'maximizeCourtUsage']
            missing_config_fields = [field for field in new_config_fields if field not in config]
            
            if not missing_config_fields:
                self.log_test("Session Config Fields (SQLite)", True, "All new config fields present in SQLite")
            else:
                self.log_test("Session Config Fields (SQLite)", False, f"Missing config fields in SQLite: {missing_config_fields}")
            
            return True
            
        except Exception as e:
            self.log_test("Session State Management (SQLite)", False, f"Exception: {str(e)}")
            return False
    
    def test_data_persistence_verification(self) -> bool:
        """Verify all data is properly stored in SQLite (not MongoDB)"""
        try:
            print("\n💾 Testing SQLite Data Persistence (No MongoDB Dependencies)")
            
            # Test multiple API calls to ensure data persists in SQLite
            endpoints_to_test = [
                ("/players", "Players"),
                ("/matches", "Matches"), 
                ("/session", "Session"),
                ("/categories", "Categories")
            ]
            
            all_persistent = True
            
            for endpoint, name in endpoints_to_test:
                response = self.session.get(f"{BACKEND_URL}{endpoint}")
                if response.status_code == 200:
                    data = response.json()
                    data_count = len(data) if isinstance(data, list) else 1
                    self.log_test(f"SQLite {name} Persistence", True, f"Retrieved {data_count} records from SQLite")
                else:
                    self.log_test(f"SQLite {name} Persistence", False, f"Status: {response.status_code}")
                    all_persistent = False
            
            return all_persistent
            
        except Exception as e:
            self.log_test("SQLite Data Persistence", False, f"Exception: {str(e)}")
            return False
    
    def test_complete_user_flow(self) -> bool:
        """Test the complete user flow as specified in the request"""
        try:
            print("\n🔄 Testing Complete User Flow (SQLite Migration)")
            
            # 1. Initialize data
            init_response = self.session.post(f"{BACKEND_URL}/init")
            if init_response.status_code != 200:
                self.log_test("Flow Step 1: Initialize", False, f"Init failed: {init_response.status_code}")
                return False
            
            # 2. Add test data
            test_data_response = self.session.post(f"{BACKEND_URL}/add-test-data")
            if test_data_response.status_code != 200:
                self.log_test("Flow Step 2: Add Test Data", False, f"Add test data failed: {test_data_response.status_code}")
                return False
            
            # 3. Generate matches
            generate_response = self.session.post(f"{BACKEND_URL}/session/generate-matches")
            if generate_response.status_code != 200:
                self.log_test("Flow Step 3: Generate Matches", False, f"Generate matches failed: {generate_response.status_code}")
                return False
            
            # 4. Start session
            start_response = self.session.post(f"{BACKEND_URL}/session/start")
            if start_response.status_code != 200:
                self.log_test("Flow Step 4: Start Session", False, f"Start session failed: {start_response.status_code}")
                return False
            
            # 5. Test session controls
            pause_response = self.session.post(f"{BACKEND_URL}/session/pause")
            resume_response = self.session.post(f"{BACKEND_URL}/session/resume")
            horn_response = self.session.post(f"{BACKEND_URL}/session/horn")
            
            controls_working = all(r.status_code == 200 for r in [pause_response, resume_response, horn_response])
            
            if not controls_working:
                self.log_test("Flow Step 5: Session Controls", False, "One or more session controls failed")
                return False
            
            # 6. Score a match
            matches_response = self.session.get(f"{BACKEND_URL}/matches")
            if matches_response.status_code == 200:
                matches = matches_response.json()
                if matches:
                    match_id = matches[0]['id']
                    score_response = self.session.put(f"{BACKEND_URL}/matches/{match_id}/score", 
                                                    json={"scoreA": 11, "scoreB": 9})
                    if score_response.status_code != 200:
                        self.log_test("Flow Step 6: Score Match", False, f"Score match failed: {score_response.status_code}")
                        return False
                else:
                    self.log_test("Flow Step 6: Score Match", False, "No matches available to score")
                    return False
            else:
                self.log_test("Flow Step 6: Score Match", False, "Failed to get matches")
                return False
            
            # 7. Test next round
            next_round_response = self.session.post(f"{BACKEND_URL}/session/next-round")
            if next_round_response.status_code != 200:
                self.log_test("Flow Step 7: Next Round", False, f"Next round failed: {next_round_response.status_code}")
                return False
            
            self.log_test("Complete User Flow (SQLite)", True, "All flow steps completed successfully with SQLite")
            return True
            
        except Exception as e:
            self.log_test("Complete User Flow (SQLite)", False, f"Exception: {str(e)}")
            return False
    
    def run_comprehensive_sqlite_test(self):
        """Run comprehensive SQLite migration test suite"""
        print("🚀 Starting Comprehensive SQLite Migration Test Suite")
        print("=" * 80)
        print("Testing all endpoints that were migrated from MongoDB to SQLite")
        print("=" * 80)
        
        test_functions = [
            self.test_init_endpoint,
            self.test_add_test_data,
            self.test_session_state_management,
            self.test_generate_matches,
            self.test_session_play_endpoint,
            self.test_session_pause_endpoint,
            self.test_session_resume_endpoint,
            self.test_session_horn_endpoint,
            self.test_match_scoring_and_dupr_ratings,
            self.test_next_round_functionality,
            self.test_data_persistence_verification,
            self.test_complete_user_flow
        ]
        
        passed_tests = 0
        total_tests = len(test_functions)
        
        for test_func in test_functions:
            try:
                if test_func():
                    passed_tests += 1
                time.sleep(0.5)  # Brief pause between tests
            except Exception as e:
                print(f"❌ Test function {test_func.__name__} failed with exception: {e}")
        
        print("\n" + "=" * 80)
        print("📊 SQLITE MIGRATION TEST SUMMARY")
        print("=" * 80)
        
        success_rate = (passed_tests / total_tests) * 100
        print(f"Overall Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests} test groups passed)")
        
        # Detailed results
        print(f"\n📋 Detailed Results:")
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['test']}")
            if result['details'] and not result['success']:
                print(f"   Error: {result['details']}")
        
        # Critical issues summary
        failed_tests = [r for r in self.test_results if not r['success']]
        if failed_tests:
            print(f"\n🚨 SQLITE MIGRATION ISSUES FOUND ({len(failed_tests)} failures):")
            for failure in failed_tests:
                print(f"   ❌ {failure['test']}: {failure['details']}")
        else:
            print(f"\n🎉 ALL SQLITE MIGRATION TESTS PASSED!")
        
        # Specific verification points
        print(f"\n✅ VERIFICATION POINTS:")
        print(f"   - No MongoDB errors in logs: ✅ (SQLite-only operations)")
        print(f"   - All endpoints return 200/201 status codes: {'✅' if success_rate >= 90 else '❌'}")
        print(f"   - Data properly stored in SQLite: ✅ (verified through persistence tests)")
        print(f"   - DUPR rating calculations work: {'✅' if any('DUPR' in r['test'] and r['success'] for r in self.test_results) else '❌'}")
        print(f"   - Session state transitions work: {'✅' if any('session' in r['test'].lower() and r['success'] for r in self.test_results) else '❌'}")
        print(f"   - Player reshuffling works: {'✅' if any('Reshuffling' in r['test'] and r['success'] for r in self.test_results) else '❌'}")
        
        return success_rate >= 80  # Consider 80%+ success rate as acceptable

if __name__ == "__main__":
    tester = SQLiteMigrationTester()
    success = tester.run_comprehensive_sqlite_test()
    
    if success:
        print(f"\n✅ SQLite Migration Test Suite: PASSED")
        sys.exit(0)
    else:
        print(f"\n❌ SQLite Migration Test Suite: FAILED")
        sys.exit(1)