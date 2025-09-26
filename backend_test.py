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
BACKEND_URL = "https://court-timer.preview.emergentagent.com/api"

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details
        })
    
    def test_add_test_data(self) -> bool:
        """Test POST /api/add-test-data - Add test players"""
        try:
            response = self.session.post(f"{BACKEND_URL}/add-test-data")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Add Test Data", True, f"Response: {data}")
                return True
            else:
                self.log_test("Add Test Data", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Add Test Data", False, f"Exception: {str(e)}")
            return False
    
    def test_get_players(self) -> bool:
        """Test GET /api/players - Verify players exist"""
        try:
            response = self.session.get(f"{BACKEND_URL}/players")
            
            if response.status_code == 200:
                players = response.json()
                player_count = len(players)
                self.log_test("Get Players", True, f"Found {player_count} players")
                
                # Show player details for verification
                if players:
                    print("   Player Details:")
                    for player in players[:3]:  # Show first 3 players
                        print(f"     - {player.get('name', 'Unknown')} ({player.get('category', 'Unknown')})")
                
                return player_count > 0
            else:
                self.log_test("Get Players", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Get Players", False, f"Exception: {str(e)}")
            return False
    
    def test_get_session_initial(self) -> Dict[str, Any]:
        """Test GET /api/session - Check initial session state"""
        try:
            response = self.session.get(f"{BACKEND_URL}/session")
            
            if response.status_code == 200:
                session = response.json()
                phase = session.get('phase', 'unknown')
                current_round = session.get('currentRound', 0)
                
                self.log_test("Get Session (Initial)", True, 
                             f"Phase: {phase}, Round: {current_round}")
                
                print(f"   Session Details:")
                print(f"     - ID: {session.get('id', 'Unknown')}")
                print(f"     - Phase: {phase}")
                print(f"     - Current Round: {current_round}")
                print(f"     - Time Remaining: {session.get('timeRemaining', 0)}")
                print(f"     - Paused: {session.get('paused', False)}")
                
                config = session.get('config', {})
                print(f"     - Config: Courts={config.get('numCourts', 0)}, PlayTime={config.get('playSeconds', 0)}s")
                
                return session
            else:
                self.log_test("Get Session (Initial)", False, f"Status: {response.status_code}, Response: {response.text}")
                return {}
                
        except Exception as e:
            self.log_test("Get Session (Initial)", False, f"Exception: {str(e)}")
            return {}
    
    def test_generate_matches(self) -> bool:
        """Test POST /api/session/generate-matches - CRITICAL TEST"""
        try:
            response = self.session.post(f"{BACKEND_URL}/session/generate-matches")
            
            if response.status_code == 200:
                session = response.json()
                phase = session.get('phase', 'unknown')
                current_round = session.get('currentRound', 0)
                
                success = phase == 'ready' and current_round == 1
                
                self.log_test("Generate Matches", success, 
                             f"Phase: {phase}, Round: {current_round} (Expected: ready, 1)")
                
                if not success:
                    print(f"   ❌ CRITICAL ISSUE: Expected phase='ready' and round=1, got phase='{phase}' and round={current_round}")
                
                return success
            else:
                self.log_test("Generate Matches", False, f"Status: {response.status_code}, Response: {response.text}")
                
                # Check if endpoint exists
                if response.status_code == 404:
                    print("   ❌ CRITICAL ISSUE: /api/session/generate-matches endpoint does not exist!")
                elif response.status_code == 500:
                    print("   ❌ CRITICAL ISSUE: Server error when generating matches!")
                
                return False
                
        except Exception as e:
            self.log_test("Generate Matches", False, f"Exception: {str(e)}")
            return False
    
    def test_get_matches(self) -> List[Dict[str, Any]]:
        """Test GET /api/matches - Check if matches were created"""
        try:
            response = self.session.get(f"{BACKEND_URL}/matches")
            
            if response.status_code == 200:
                matches = response.json()
                match_count = len(matches)
                
                success = match_count > 0
                self.log_test("Get Matches", success, f"Found {match_count} matches")
                
                if matches:
                    print("   Match Details:")
                    for i, match in enumerate(matches[:3]):  # Show first 3 matches
                        court = match.get('courtIndex', 'Unknown')
                        category = match.get('category', 'Unknown')
                        team_a = match.get('teamA', [])
                        team_b = match.get('teamB', [])
                        match_type = match.get('matchType', 'Unknown')
                        status = match.get('status', 'Unknown')
                        
                        print(f"     Match {i+1}: Court {court}, {category}, {match_type}")
                        print(f"       Team A: {len(team_a)} players, Team B: {len(team_b)} players")
                        print(f"       Status: {status}")
                else:
                    print("   ❌ CRITICAL ISSUE: No matches found after generate-matches!")
                
                return matches
            else:
                self.log_test("Get Matches", False, f"Status: {response.status_code}, Response: {response.text}")
                return []
                
        except Exception as e:
            self.log_test("Get Matches", False, f"Exception: {str(e)}")
            return []
    
    def test_session_after_generate(self) -> Dict[str, Any]:
        """Test GET /api/session - Verify session state after generate matches"""
        try:
            response = self.session.get(f"{BACKEND_URL}/session")
            
            if response.status_code == 200:
                session = response.json()
                phase = session.get('phase', 'unknown')
                current_round = session.get('currentRound', 0)
                
                expected_phase = 'ready'
                expected_round = 1
                
                success = phase == expected_phase and current_round == expected_round
                
                self.log_test("Session After Generate", success, 
                             f"Phase: {phase}, Round: {current_round} (Expected: {expected_phase}, {expected_round})")
                
                if not success:
                    print(f"   ❌ ISSUE: Session should be in 'ready' phase with round 1 after generating matches")
                    print(f"   Current state: phase='{phase}', round={current_round}")
                
                return session
            else:
                self.log_test("Session After Generate", False, f"Status: {response.status_code}, Response: {response.text}")
                return {}
                
        except Exception as e:
            self.log_test("Session After Generate", False, f"Exception: {str(e)}")
            return {}
    
    def test_start_session(self) -> bool:
        """Test POST /api/session/start - Let's Play button functionality"""
        try:
            response = self.session.post(f"{BACKEND_URL}/session/start")
            
            if response.status_code == 200:
                session = response.json()
                phase = session.get('phase', 'unknown')
                current_round = session.get('currentRound', 0)
                
                expected_phase = 'play'
                expected_round = 1
                
                success = phase == expected_phase and current_round == expected_round
                
                self.log_test("Start Session (Let's Play)", success, 
                             f"Phase: {phase}, Round: {current_round} (Expected: {expected_phase}, {expected_round})")
                
                if not success:
                    print(f"   ❌ ISSUE: Let's Play button should transition to 'play' phase")
                    print(f"   Current state: phase='{phase}', round={current_round}")
                
                return success
            else:
                self.log_test("Start Session (Let's Play)", False, f"Status: {response.status_code}, Response: {response.text}")
                
                if response.status_code == 400:
                    print("   ❌ ISSUE: Session start failed - might not be in correct phase")
                    print(f"   Response: {response.text}")
                
                return False
                
        except Exception as e:
            self.log_test("Start Session (Let's Play)", False, f"Exception: {str(e)}")
            return False
    
    def test_session_after_start(self) -> Dict[str, Any]:
        """Test GET /api/session - Verify session state after start"""
        try:
            response = self.session.get(f"{BACKEND_URL}/session")
            
            if response.status_code == 200:
                session = response.json()
                phase = session.get('phase', 'unknown')
                current_round = session.get('currentRound', 0)
                time_remaining = session.get('timeRemaining', 0)
                
                expected_phase = 'play'
                expected_round = 1
                
                success = phase == expected_phase and current_round == expected_round
                
                self.log_test("Session After Start", success, 
                             f"Phase: {phase}, Round: {current_round}, Time: {time_remaining}s")
                
                if success:
                    print("   ✅ SUCCESS: Session is now in play phase with timer running")
                else:
                    print(f"   ❌ ISSUE: Expected play phase with round 1, got phase='{phase}', round={current_round}")
                
                return session
            else:
                self.log_test("Session After Start", False, f"Status: {response.status_code}, Response: {response.text}")
                return {}
                
        except Exception as e:
            self.log_test("Session After Start", False, f"Exception: {str(e)}")
            return {}
    
    def test_court_assignments(self, matches: List[Dict[str, Any]]) -> bool:
        """Test court assignments in matches"""
        if not matches:
            self.log_test("Court Assignments", False, "No matches to test court assignments")
            return False
        
        try:
            court_indices = [match.get('courtIndex') for match in matches]
            unique_courts = set(court_indices)
            
            # Check if court indices are valid (0-based indexing)
            valid_courts = all(isinstance(court, int) and court >= 0 for court in court_indices)
            
            success = valid_courts and len(unique_courts) > 0
            
            self.log_test("Court Assignments", success, 
                         f"Courts used: {sorted(unique_courts)}, Total matches: {len(matches)}")
            
            if not success:
                print(f"   ❌ ISSUE: Invalid court assignments found")
                print(f"   Court indices: {court_indices}")
            
            return success
            
        except Exception as e:
            self.log_test("Court Assignments", False, f"Exception: {str(e)}")
            return False
    
    def run_comprehensive_test(self):
        """Run comprehensive test of match generation and courts functionality"""
        print("=" * 80)
        print("🏓 COURTCHIME BACKEND TESTING - MATCH GENERATION & COURTS FUNCTIONALITY")
        print("=" * 80)
        print(f"Backend URL: {BACKEND_URL}")
        print()
        
        # Test sequence based on user's reported issues
        print("📋 TESTING SEQUENCE:")
        print("1. Add test players")
        print("2. Check initial session state")
        print("3. Generate matches (CRITICAL TEST)")
        print("4. Verify matches were created")
        print("5. Check session is in 'ready' phase")
        print("6. Start session (Let's Play button)")
        print("7. Verify session is in 'play' phase")
        print("8. Test court assignments")
        print()
        
        # Step 1: Add test data
        print("🔄 Step 1: Adding test players...")
        players_added = self.test_add_test_data()
        
        if players_added:
            self.test_get_players()
        
        print()
        
        # Step 2: Check initial session
        print("🔄 Step 2: Checking initial session state...")
        initial_session = self.test_get_session_initial()
        print()
        
        # Step 3: Generate matches (CRITICAL)
        print("🔄 Step 3: Generating matches (CRITICAL TEST)...")
        matches_generated = self.test_generate_matches()
        print()
        
        # Step 4: Check matches were created
        print("🔄 Step 4: Verifying matches were created...")
        matches = self.test_get_matches()
        print()
        
        # Step 5: Check session state after generate
        print("🔄 Step 5: Checking session state after generate...")
        ready_session = self.test_session_after_generate()
        print()
        
        # Step 6: Start session (Let's Play)
        print("🔄 Step 6: Starting session (Let's Play button)...")
        session_started = self.test_start_session()
        print()
        
        # Step 7: Check session state after start
        print("🔄 Step 7: Verifying session state after start...")
        play_session = self.test_session_after_start()
        print()
        
        # Step 8: Test court assignments
        print("🔄 Step 8: Testing court assignments...")
        court_assignments_valid = self.test_court_assignments(matches)
        print()
        
        # Summary
        self.print_summary()
        
        return self.test_results
    
    def print_summary(self):
        """Print test summary"""
        print("=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Tests Passed: {passed}/{total} ({passed/total*100:.1f}%)")
        print()
        
        # Critical issues
        critical_issues = []
        
        for result in self.test_results:
            if not result['success']:
                if 'Generate Matches' in result['test']:
                    critical_issues.append("❌ CRITICAL: Generate Matches functionality is broken")
                elif 'Let\'s Play' in result['test'] or 'Start Session' in result['test']:
                    critical_issues.append("❌ CRITICAL: Let's Play button functionality is broken")
                elif 'Get Matches' in result['test'] and 'Found 0 matches' in result['details']:
                    critical_issues.append("❌ CRITICAL: No matches created after generate-matches")
        
        if critical_issues:
            print("🚨 CRITICAL ISSUES FOUND:")
            for issue in critical_issues:
                print(f"   {issue}")
            print()
        
        # Failed tests
        failed_tests = [result for result in self.test_results if not result['success']]
        if failed_tests:
            print("❌ FAILED TESTS:")
            for result in failed_tests:
                print(f"   - {result['test']}: {result['details']}")
            print()
        
        # Success tests
        passed_tests = [result for result in self.test_results if result['success']]
        if passed_tests:
            print("✅ PASSED TESTS:")
            for result in passed_tests:
                print(f"   - {result['test']}")
            print()
        
        print("=" * 80)

def main():
    """Main test execution"""
    tester = BackendTester()
    results = tester.run_comprehensive_test()
    
    # Exit with error code if any critical tests failed
    critical_failures = any(
        not result['success'] and ('Generate Matches' in result['test'] or 'Start Session' in result['test'])
        for result in results
    )
    
    if critical_failures:
        print("🚨 CRITICAL FAILURES DETECTED - EXITING WITH ERROR CODE")
        sys.exit(1)
    else:
        print("✅ ALL CRITICAL TESTS PASSED")
        sys.exit(0)

if __name__ == "__main__":
    main()