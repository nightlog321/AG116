#!/usr/bin/env python3
"""
Enhanced Player Reshuffling Algorithm Testing Suite
Tests the FIXED integration between enhanced algorithms and /api/session/next-round endpoint
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any

# Use the production URL from frontend/.env
BACKEND_URL = "https://court-timer.preview.emergentagent.com/api"

class EnhancedReshufflingTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        
    def log_result(self, test_name: str, success: bool, details: str):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status}: {test_name} - {details}"
        print(result)
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details
        })
        
    def make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make HTTP request with error handling"""
        try:
            url = f"{BACKEND_URL}{endpoint}"
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {method} {endpoint} - {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response text: {e.response.text[:500]}")
            return {"error": str(e)}
            
    def setup_test_environment(self) -> bool:
        """Setup test environment with diverse players"""
        print("\n🔧 SETTING UP TEST ENVIRONMENT...")
        
        # Add test data with 12 diverse players
        result = self.make_request("POST", "/add-test-data")
        if "error" in result:
            self.log_result("Setup Test Data", False, f"Failed to add test data: {result['error']}")
            return False
            
        # Verify players were created
        players = self.make_request("GET", "/players")
        if "error" in players or len(players) < 12:
            self.log_result("Setup Verification", False, f"Expected 12+ players, got {len(players) if 'error' not in players else 'error'}")
            return False
            
        self.log_result("Setup Test Data", True, f"Successfully created {len(players)} diverse players")
        return True
        
    def test_enhanced_reshuffling_verification(self) -> bool:
        """Test 1: Enhanced Reshuffling Verification"""
        print("\n🔄 TEST 1: ENHANCED RESHUFFLING VERIFICATION")
        
        try:
            # Generate Round 1 matches
            result = self.make_request("POST", "/session/generate-matches")
            if "error" in result:
                self.log_result("Round 1 Generation", False, f"Failed to generate Round 1: {result['error']}")
                return False
                
            # Get Round 1 teams
            round1_matches = self.make_request("GET", "/matches")
            if "error" in round1_matches:
                self.log_result("Round 1 Matches Fetch", False, f"Failed to fetch Round 1 matches: {round1_matches['error']}")
                return False
                
            round1_teams = []
            for match in round1_matches:
                if match.get('roundIndex') == 1:
                    round1_teams.append({
                        'teamA': sorted(match['teamA']),
                        'teamB': sorted(match['teamB']),
                        'category': match['category']
                    })
                    
            if not round1_teams:
                self.log_result("Round 1 Teams", False, "No Round 1 matches found")
                return False
                
            self.log_result("Round 1 Generation", True, f"Generated {len(round1_teams)} matches")
            
            # Progress to Round 2 using ENHANCED ALGORITHM via /api/session/next-round
            result = self.make_request("POST", "/session/next-round")
            if "error" in result:
                self.log_result("Round 2 Progression", False, f"Failed to progress to Round 2: {result['error']}")
                return False
                
            # Get Round 2 teams
            all_matches = self.make_request("GET", "/matches")
            if "error" in all_matches:
                self.log_result("Round 2 Matches Fetch", False, f"Failed to fetch Round 2 matches: {all_matches['error']}")
                return False
                
            round2_teams = []
            for match in all_matches:
                if match.get('roundIndex') == 2:
                    round2_teams.append({
                        'teamA': sorted(match['teamA']),
                        'teamB': sorted(match['teamB']),
                        'category': match['category']
                    })
                    
            if not round2_teams:
                self.log_result("Round 2 Teams", False, "No Round 2 matches found - Enhanced algorithm not working")
                return False
                
            # Calculate reshuffling effectiveness
            identical_teams = 0
            total_teams = len(round1_teams) * 2  # Each match has 2 teams
            
            for r1_match in round1_teams:
                for r2_match in round2_teams:
                    if (r1_match['teamA'] == r2_match['teamA'] or 
                        r1_match['teamA'] == r2_match['teamB'] or
                        r1_match['teamB'] == r2_match['teamA'] or 
                        r1_match['teamB'] == r2_match['teamB']):
                        identical_teams += 1
                        
            reshuffling_effectiveness = ((total_teams - identical_teams) / total_teams) * 100 if total_teams > 0 else 0
            
            self.log_result("Round 2 Generation", True, f"Generated {len(round2_teams)} matches")
            
            # Test Round 3 for additional verification
            result = self.make_request("POST", "/session/next-round")
            if "error" not in result:
                all_matches = self.make_request("GET", "/matches")
                round3_teams = [match for match in all_matches if match.get('roundIndex') == 3]
                self.log_result("Round 3 Generation", True, f"Generated {len(round3_teams)} matches")
            
            # SUCCESS CRITERIA: 60%+ variation
            success = reshuffling_effectiveness >= 60.0
            self.log_result("Enhanced Reshuffling Effectiveness", success, 
                          f"Reshuffling effectiveness: {reshuffling_effectiveness:.1f}% (target: 60%+)")
            
            return success
            
        except Exception as e:
            self.log_result("Enhanced Reshuffling Test", False, f"Exception: {str(e)}")
            return False
            
    def test_history_tracking_verification(self) -> bool:
        """Test 2: History Tracking Verification"""
        print("\n📊 TEST 2: HISTORY TRACKING VERIFICATION")
        
        try:
            # Get session to check histories
            session_data = self.make_request("GET", "/session")
            if "error" in session_data:
                self.log_result("Session Data Fetch", False, f"Failed to fetch session: {session_data['error']}")
                return False
                
            histories = session_data.get('histories', {})
            partner_history = histories.get('partnerHistory', {})
            opponent_history = histories.get('opponentHistory', {})
            
            # Count history entries
            partner_entries = sum(len(partners) for partners in partner_history.values())
            opponent_entries = sum(len(opponents) for opponents in opponent_history.values())
            
            self.log_result("Partner History Tracking", partner_entries > 0, 
                          f"Partner history entries: {partner_entries}")
            self.log_result("Opponent History Tracking", opponent_entries > 0, 
                          f"Opponent history entries: {opponent_entries}")
            
            # Verify history structure
            history_structure_valid = True
            if partner_history:
                for player_id, partners in partner_history.items():
                    if not isinstance(partners, dict):
                        history_structure_valid = False
                        break
                        
            if opponent_history:
                for player_id, opponents in opponent_history.items():
                    if not isinstance(opponents, dict):
                        history_structure_valid = False
                        break
                        
            self.log_result("History Structure Validation", history_structure_valid, 
                          "History data structure is valid")
            
            # SUCCESS CRITERIA: Both histories populated
            success = partner_entries > 0 and opponent_entries > 0 and history_structure_valid
            return success
            
        except Exception as e:
            self.log_result("History Tracking Test", False, f"Exception: {str(e)}")
            return False
            
    def test_rating_balance_verification(self) -> bool:
        """Test 3: Rating Balance Testing"""
        print("\n⚖️ TEST 3: RATING BALANCE TESTING")
        
        try:
            # Get all players with ratings
            players = self.make_request("GET", "/players")
            if "error" in players:
                self.log_result("Players Fetch", False, f"Failed to fetch players: {players['error']}")
                return False
                
            # Get current matches
            matches = self.make_request("GET", "/matches")
            if "error" in matches:
                self.log_result("Matches Fetch", False, f"Failed to fetch matches: {matches['error']}")
                return False
                
            # Create player rating lookup
            player_ratings = {p['id']: p['rating'] for p in players}
            
            # Calculate rating balance for each match
            rating_differences = []
            balanced_matches = 0
            
            for match in matches:
                if match.get('roundIndex', 0) >= 2:  # Focus on enhanced algorithm rounds
                    team_a_ratings = [player_ratings.get(pid, 3.0) for pid in match['teamA']]
                    team_b_ratings = [player_ratings.get(pid, 3.0) for pid in match['teamB']]
                    
                    team_a_avg = sum(team_a_ratings) / len(team_a_ratings) if team_a_ratings else 3.0
                    team_b_avg = sum(team_b_ratings) / len(team_b_ratings) if team_b_ratings else 3.0
                    
                    rating_diff = abs(team_a_avg - team_b_avg)
                    rating_differences.append(rating_diff)
                    
                    # Consider match balanced if rating difference < 0.5
                    if rating_diff < 0.5:
                        balanced_matches += 1
                        
            if rating_differences:
                avg_rating_diff = sum(rating_differences) / len(rating_differences)
                balance_percentage = (balanced_matches / len(rating_differences)) * 100
                
                self.log_result("Rating Balance Analysis", True, 
                              f"Average rating difference: {avg_rating_diff:.2f}, Balanced matches: {balance_percentage:.1f}%")
                
                # SUCCESS CRITERIA: Average difference < 0.6 OR 50%+ balanced matches
                success = avg_rating_diff < 0.6 or balance_percentage >= 50.0
                self.log_result("Enhanced Rating Balance", success, 
                              f"Rating balance optimization {'working' if success else 'needs improvement'}")
                return success
            else:
                self.log_result("Rating Balance Analysis", False, "No matches found for analysis")
                return False
                
        except Exception as e:
            self.log_result("Rating Balance Test", False, f"Exception: {str(e)}")
            return False
            
    def test_algorithm_performance(self) -> bool:
        """Test 4: Multiple Algorithm Attempts"""
        print("\n🚀 TEST 4: ALGORITHM PERFORMANCE TESTING")
        
        try:
            # Test algorithm stability across multiple rounds
            performance_results = []
            
            for round_num in range(4, 7):  # Test rounds 4-6
                start_time = time.time()
                result = self.make_request("POST", "/session/next-round")
                end_time = time.time()
                
                if "error" not in result:
                    response_time = (end_time - start_time) * 1000  # Convert to ms
                    performance_results.append(response_time)
                    
                    # Verify matches were created
                    matches = self.make_request("GET", "/matches")
                    round_matches = [m for m in matches if m.get('roundIndex') == round_num]
                    
                    self.log_result(f"Round {round_num} Performance", True, 
                                  f"Generated {len(round_matches)} matches in {response_time:.0f}ms")
                else:
                    self.log_result(f"Round {round_num} Performance", False, 
                                  f"Failed to generate round: {result['error']}")
                    
            if performance_results:
                avg_response_time = sum(performance_results) / len(performance_results)
                max_response_time = max(performance_results)
                
                # SUCCESS CRITERIA: Average < 2000ms, Max < 5000ms
                performance_good = avg_response_time < 2000 and max_response_time < 5000
                
                self.log_result("Algorithm Performance", performance_good, 
                              f"Avg: {avg_response_time:.0f}ms, Max: {max_response_time:.0f}ms")
                return performance_good
            else:
                self.log_result("Algorithm Performance", False, "No performance data collected")
                return False
                
        except Exception as e:
            self.log_result("Algorithm Performance Test", False, f"Exception: {str(e)}")
            return False
            
    def test_integration_verification(self) -> bool:
        """Test 5: Integration Verification"""
        print("\n🔗 TEST 5: INTEGRATION VERIFICATION")
        
        try:
            # Verify /api/session/next-round uses enhanced algorithms
            # This is tested indirectly through the reshuffling effectiveness
            
            # Get session state
            session = self.make_request("GET", "/session")
            if "error" in session:
                self.log_result("Session State", False, f"Failed to get session: {session['error']}")
                return False
                
            current_round = session.get('currentRound', 0)
            phase = session.get('phase', 'unknown')
            
            self.log_result("Session State", True, f"Round {current_round}, Phase: {phase}")
            
            # Verify enhanced features are accessible
            config = session.get('config', {})
            has_enhanced_config = all(key in config for key in ['allowSingles', 'allowDoubles', 'allowCrossCategory'])
            
            self.log_result("Enhanced Configuration", has_enhanced_config, 
                          f"Enhanced config fields present: {has_enhanced_config}")
            
            # Test that next-round endpoint is responsive
            result = self.make_request("POST", "/session/next-round")
            next_round_working = "error" not in result
            
            self.log_result("Next Round Endpoint", next_round_working, 
                          f"Next round endpoint {'working' if next_round_working else 'failed'}")
            
            return has_enhanced_config and next_round_working
            
        except Exception as e:
            self.log_result("Integration Verification", False, f"Exception: {str(e)}")
            return False
            
    def run_comprehensive_test(self):
        """Run all enhanced reshuffling algorithm tests"""
        print("🏓 ENHANCED PLAYER RESHUFFLING ALGORITHM - COMPREHENSIVE TESTING")
        print("=" * 80)
        
        # Setup
        if not self.setup_test_environment():
            print("\n❌ SETUP FAILED - Cannot proceed with testing")
            return
            
        # Run all tests
        test_results = []
        test_results.append(self.test_enhanced_reshuffling_verification())
        test_results.append(self.test_history_tracking_verification())
        test_results.append(self.test_rating_balance_verification())
        test_results.append(self.test_algorithm_performance())
        test_results.append(self.test_integration_verification())
        
        # Summary
        passed_tests = sum(test_results)
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests) * 100
        
        print("\n" + "=" * 80)
        print("📊 ENHANCED RESHUFFLING ALGORITHM TEST SUMMARY")
        print("=" * 80)
        
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['test']}: {result['details']}")
            
        print(f"\n🎯 OVERALL RESULT: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
        
        if success_rate >= 80:
            print("🎉 ENHANCED RESHUFFLING ALGORITHM IS WORKING EXCELLENTLY!")
        elif success_rate >= 60:
            print("✅ ENHANCED RESHUFFLING ALGORITHM IS WORKING WELL!")
        else:
            print("❌ ENHANCED RESHUFFLING ALGORITHM NEEDS FIXES!")
            
        return success_rate >= 60

if __name__ == "__main__":
    tester = EnhancedReshufflingTester()
    success = tester.run_comprehensive_test()
    sys.exit(0 if success else 1)