#!/usr/bin/env python3
"""
Enhanced Player Reshuffling Algorithm Testing Suite
Tests the new enhanced shuffling, rating balance, and history tracking features
"""

import requests
import json
import time
from typing import Dict, List, Any
import statistics

# Backend URL from environment
BACKEND_URL = "https://court-timer.preview.emergentagent.com/api"

class EnhancedReshufflingTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        
    def log_result(self, test_name: str, success: bool, message: str, details: Dict = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {}
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details:
            print(f"   Details: {details}")
    
    def setup_test_environment(self):
        """Setup test environment with diverse players"""
        print("\n🔧 SETTING UP TEST ENVIRONMENT...")
        
        try:
            # Add diverse test players using the existing add-test-data endpoint
            response = self.session.post(f"{BACKEND_URL}/add-test-data")
            if response.status_code != 200:
                self.log_result("Environment Setup", False, f"Failed to add test data: {response.status_code}")
                return False
            
            # Verify players were created
            response = self.session.get(f"{BACKEND_URL}/players")
            if response.status_code != 200:
                self.log_result("Environment Setup", False, f"Failed to get players: {response.status_code}")
                return False
            
            players = response.json()
            self.log_result("Environment Setup", True, f"Created {len(players)} diverse test players")
            return True
            
        except Exception as e:
            self.log_result("Environment Setup", False, f"Exception: {str(e)}")
            return False
    
    def test_basic_reshuffling_verification(self):
        """Test 1: Basic Reshuffling Verification - Teams should be different across rounds"""
        print("\n🔄 TEST 1: BASIC RESHUFFLING VERIFICATION")
        
        try:
            # Generate Round 1
            response = self.session.post(f"{BACKEND_URL}/session/generate-matches")
            if response.status_code != 200:
                self.log_result("Basic Reshuffling", False, f"Failed to generate Round 1: {response.status_code}")
                return
            
            # Get Round 1 matches
            response = self.session.get(f"{BACKEND_URL}/matches")
            if response.status_code != 200:
                self.log_result("Basic Reshuffling", False, f"Failed to get Round 1 matches: {response.status_code}")
                return
            
            round1_matches = response.json()
            round1_teams = []
            for match in round1_matches:
                if match['roundIndex'] == 1:
                    team_a = tuple(sorted(match['teamA']))
                    team_b = tuple(sorted(match['teamB']))
                    round1_teams.extend([team_a, team_b])
            
            # Start session and progress to Round 2
            response = self.session.post(f"{BACKEND_URL}/session/start")
            if response.status_code != 200:
                self.log_result("Basic Reshuffling", False, f"Failed to start session: {response.status_code}")
                return
            
            # Generate Round 2
            response = self.session.post(f"{BACKEND_URL}/session/next-round")
            if response.status_code != 200:
                self.log_result("Basic Reshuffling", False, f"Failed to generate Round 2: {response.status_code}")
                return
            
            # Get Round 2 matches
            response = self.session.get(f"{BACKEND_URL}/matches")
            if response.status_code != 200:
                self.log_result("Basic Reshuffling", False, f"Failed to get Round 2 matches: {response.status_code}")
                return
            
            all_matches = response.json()
            round2_matches = [m for m in all_matches if m['roundIndex'] == 2]
            round2_teams = []
            for match in round2_matches:
                team_a = tuple(sorted(match['teamA']))
                team_b = tuple(sorted(match['teamB']))
                round2_teams.extend([team_a, team_b])
            
            # Generate Round 3
            response = self.session.post(f"{BACKEND_URL}/session/next-round")
            if response.status_code != 200:
                self.log_result("Basic Reshuffling", False, f"Failed to generate Round 3: {response.status_code}")
                return
            
            # Get Round 3 matches
            response = self.session.get(f"{BACKEND_URL}/matches")
            if response.status_code != 200:
                self.log_result("Basic Reshuffling", False, f"Failed to get Round 3 matches: {response.status_code}")
                return
            
            all_matches = response.json()
            round3_matches = [m for m in all_matches if m['roundIndex'] == 3]
            round3_teams = []
            for match in round3_matches:
                team_a = tuple(sorted(match['teamA']))
                team_b = tuple(sorted(match['teamB']))
                round3_teams.extend([team_a, team_b])
            
            # Check for team variety across rounds
            identical_teams_r1_r2 = len(set(round1_teams) & set(round2_teams))
            identical_teams_r2_r3 = len(set(round2_teams) & set(round3_teams))
            identical_teams_r1_r3 = len(set(round1_teams) & set(round3_teams))
            
            total_teams_r1 = len(round1_teams)
            total_teams_r2 = len(round2_teams)
            total_teams_r3 = len(round3_teams)
            
            # Calculate reshuffling effectiveness
            total_possible_identical = total_teams_r1 + total_teams_r2 + total_teams_r3
            actual_identical = identical_teams_r1_r2 + identical_teams_r2_r3 + identical_teams_r1_r3
            reshuffling_score = 1.0 - (actual_identical / total_possible_identical) if total_possible_identical > 0 else 0
            
            details = {
                "round1_teams": len(round1_teams),
                "round2_teams": len(round2_teams),
                "round3_teams": len(round3_teams),
                "identical_r1_r2": identical_teams_r1_r2,
                "identical_r2_r3": identical_teams_r2_r3,
                "identical_r1_r3": identical_teams_r1_r3,
                "reshuffling_effectiveness": f"{reshuffling_score:.2%}"
            }
            
            # Success if less than 30% teams are identical across rounds
            success = reshuffling_score > 0.7
            message = f"Reshuffling effectiveness: {reshuffling_score:.2%}"
            
            self.log_result("Basic Reshuffling", success, message, details)
            
        except Exception as e:
            self.log_result("Basic Reshuffling", False, f"Exception: {str(e)}")
    
    def test_rating_balance_verification(self):
        """Test 2: Rating Balance Testing - Verify better rating balance across matches"""
        print("\n⚖️ TEST 2: RATING BALANCE VERIFICATION")
        
        try:
            # Get current players to analyze their ratings
            response = self.session.get(f"{BACKEND_URL}/players")
            if response.status_code != 200:
                self.log_result("Rating Balance", False, f"Failed to get players: {response.status_code}")
                return
            
            players = response.json()
            player_ratings = {p['id']: p['rating'] for p in players}
            
            # Get current matches
            response = self.session.get(f"{BACKEND_URL}/matches")
            if response.status_code != 200:
                self.log_result("Rating Balance", False, f"Failed to get matches: {response.status_code}")
                return
            
            matches = response.json()
            
            # Analyze rating balance for each match
            rating_differences = []
            team_averages = []
            
            for match in matches:
                if match['matchType'] == 'doubles' and len(match['teamA']) == 2 and len(match['teamB']) == 2:
                    # Calculate team averages
                    team_a_ratings = [player_ratings.get(pid, 3.0) for pid in match['teamA']]
                    team_b_ratings = [player_ratings.get(pid, 3.0) for pid in match['teamB']]
                    
                    team_a_avg = sum(team_a_ratings) / len(team_a_ratings)
                    team_b_avg = sum(team_b_ratings) / len(team_b_ratings)
                    
                    rating_diff = abs(team_a_avg - team_b_avg)
                    rating_differences.append(rating_diff)
                    team_averages.extend([team_a_avg, team_b_avg])
                
                elif match['matchType'] == 'singles':
                    # Singles match rating difference
                    player_a_rating = player_ratings.get(match['teamA'][0], 3.0)
                    player_b_rating = player_ratings.get(match['teamB'][0], 3.0)
                    
                    rating_diff = abs(player_a_rating - player_b_rating)
                    rating_differences.append(rating_diff)
                    team_averages.extend([player_a_rating, player_b_rating])
            
            if not rating_differences:
                self.log_result("Rating Balance", False, "No matches found to analyze")
                return
            
            # Calculate balance metrics
            avg_rating_diff = statistics.mean(rating_differences)
            max_rating_diff = max(rating_differences)
            min_rating_diff = min(rating_differences)
            rating_variance = statistics.variance(team_averages) if len(team_averages) > 1 else 0
            
            # Good balance criteria: average difference < 1.0, max difference < 2.0
            balance_score = 1.0 - min(avg_rating_diff / 2.0, 1.0)  # Normalize to 0-1 scale
            
            details = {
                "matches_analyzed": len(rating_differences),
                "avg_rating_difference": round(avg_rating_diff, 2),
                "max_rating_difference": round(max_rating_diff, 2),
                "min_rating_difference": round(min_rating_diff, 2),
                "rating_variance": round(rating_variance, 2),
                "balance_score": f"{balance_score:.2%}"
            }
            
            # Success if average rating difference is reasonable (< 1.5 points)
            success = avg_rating_diff < 1.5 and max_rating_diff < 3.0
            message = f"Average rating difference: {avg_rating_diff:.2f}, Balance score: {balance_score:.2%}"
            
            self.log_result("Rating Balance", success, message, details)
            
        except Exception as e:
            self.log_result("Rating Balance", False, f"Exception: {str(e)}")
    
    def test_history_tracking_verification(self):
        """Test 3: History Tracking Verification - Check partnerHistory and opponentHistory updates"""
        print("\n📊 TEST 3: HISTORY TRACKING VERIFICATION")
        
        try:
            # Get session to check histories
            response = self.session.get(f"{BACKEND_URL}/session")
            if response.status_code != 200:
                self.log_result("History Tracking", False, f"Failed to get session: {response.status_code}")
                return
            
            session_data = response.json()
            histories = session_data.get('histories', {})
            
            partner_history = histories.get('partnerHistory', {})
            opponent_history = histories.get('opponentHistory', {})
            
            # Get matches to verify history tracking
            response = self.session.get(f"{BACKEND_URL}/matches")
            if response.status_code != 200:
                self.log_result("History Tracking", False, f"Failed to get matches: {response.status_code}")
                return
            
            matches = response.json()
            
            # Count expected partnerships and opponents from matches
            expected_partnerships = {}
            expected_opponents = {}
            
            for match in matches:
                # Count partnerships (for doubles)
                if match['matchType'] == 'doubles' and len(match['teamA']) == 2 and len(match['teamB']) == 2:
                    # Team A partnerships
                    p1, p2 = match['teamA'][0], match['teamA'][1]
                    if p1 not in expected_partnerships:
                        expected_partnerships[p1] = {}
                    if p2 not in expected_partnerships:
                        expected_partnerships[p2] = {}
                    expected_partnerships[p1][p2] = expected_partnerships[p1].get(p2, 0) + 1
                    expected_partnerships[p2][p1] = expected_partnerships[p2].get(p1, 0) + 1
                    
                    # Team B partnerships
                    p1, p2 = match['teamB'][0], match['teamB'][1]
                    if p1 not in expected_partnerships:
                        expected_partnerships[p1] = {}
                    if p2 not in expected_partnerships:
                        expected_partnerships[p2] = {}
                    expected_partnerships[p1][p2] = expected_partnerships[p1].get(p2, 0) + 1
                    expected_partnerships[p2][p1] = expected_partnerships[p2].get(p1, 0) + 1
                
                # Count opponents
                for player_a in match['teamA']:
                    for player_b in match['teamB']:
                        if player_a not in expected_opponents:
                            expected_opponents[player_a] = {}
                        if player_b not in expected_opponents:
                            expected_opponents[player_b] = {}
                        expected_opponents[player_a][player_b] = expected_opponents[player_a].get(player_b, 0) + 1
                        expected_opponents[player_b][player_a] = expected_opponents[player_b].get(player_a, 0) + 1
            
            # Verify history accuracy
            partner_matches = 0
            partner_errors = 0
            opponent_matches = 0
            opponent_errors = 0
            
            # Check partner history accuracy
            for player_id, partners in expected_partnerships.items():
                for partner_id, count in partners.items():
                    recorded_count = partner_history.get(player_id, {}).get(partner_id, 0)
                    if recorded_count == count:
                        partner_matches += 1
                    else:
                        partner_errors += 1
            
            # Check opponent history accuracy
            for player_id, opponents in expected_opponents.items():
                for opponent_id, count in opponents.items():
                    recorded_count = opponent_history.get(player_id, {}).get(opponent_id, 0)
                    if recorded_count == count:
                        opponent_matches += 1
                    else:
                        opponent_errors += 1
            
            # Calculate accuracy
            total_partner_entries = partner_matches + partner_errors
            total_opponent_entries = opponent_matches + opponent_errors
            
            partner_accuracy = partner_matches / total_partner_entries if total_partner_entries > 0 else 1.0
            opponent_accuracy = opponent_matches / total_opponent_entries if total_opponent_entries > 0 else 1.0
            
            details = {
                "partner_history_entries": len(partner_history),
                "opponent_history_entries": len(opponent_history),
                "partner_accuracy": f"{partner_accuracy:.2%}",
                "opponent_accuracy": f"{opponent_accuracy:.2%}",
                "partner_matches": partner_matches,
                "partner_errors": partner_errors,
                "opponent_matches": opponent_matches,
                "opponent_errors": opponent_errors,
                "total_matches_analyzed": len(matches)
            }
            
            # Success if both histories have good accuracy (>90%)
            success = partner_accuracy >= 0.9 and opponent_accuracy >= 0.9 and len(partner_history) > 0 and len(opponent_history) > 0
            message = f"Partner accuracy: {partner_accuracy:.2%}, Opponent accuracy: {opponent_accuracy:.2%}"
            
            self.log_result("History Tracking", success, message, details)
            
        except Exception as e:
            self.log_result("History Tracking", False, f"Exception: {str(e)}")
    
    def test_enhanced_algorithm_performance(self):
        """Test 4: Enhanced Algorithm Performance - Test with varying player counts"""
        print("\n🚀 TEST 4: ENHANCED ALGORITHM PERFORMANCE")
        
        try:
            # Test different player count scenarios
            test_scenarios = [
                {"players": 6, "description": "Small group (6 players)"},
                {"players": 8, "description": "Medium group (8 players)"},
                {"players": 12, "description": "Large group (12 players)"},
                {"players": 15, "description": "Extra large group (15 players)"}
            ]
            
            scenario_results = []
            
            for scenario in test_scenarios:
                print(f"   Testing scenario: {scenario['description']}")
                
                # Reset environment
                self.session.delete(f"{BACKEND_URL}/clear-all-data")
                self.session.post(f"{BACKEND_URL}/init")
                
                # Create players for this scenario
                for i in range(scenario['players']):
                    categories = ["Beginner", "Intermediate", "Advanced"]
                    category = categories[i % 3]
                    player_data = {
                        "name": f"Player{i+1}",
                        "category": category
                    }
                    self.session.post(f"{BACKEND_URL}/players", json=player_data)
                
                # Test match generation
                start_time = time.time()
                response = self.session.post(f"{BACKEND_URL}/session/generate-matches")
                generation_time = time.time() - start_time
                
                if response.status_code != 200:
                    scenario_results.append({
                        "scenario": scenario['description'],
                        "success": False,
                        "error": f"Failed to generate matches: {response.status_code}"
                    })
                    continue
                
                # Get matches and analyze
                response = self.session.get(f"{BACKEND_URL}/matches")
                if response.status_code != 200:
                    scenario_results.append({
                        "scenario": scenario['description'],
                        "success": False,
                        "error": f"Failed to get matches: {response.status_code}"
                    })
                    continue
                
                matches = response.json()
                
                # Calculate metrics
                total_matches = len(matches)
                players_in_matches = set()
                for match in matches:
                    players_in_matches.update(match['teamA'] + match['teamB'])
                
                participation_rate = len(players_in_matches) / scenario['players']
                
                scenario_results.append({
                    "scenario": scenario['description'],
                    "success": True,
                    "players": scenario['players'],
                    "matches_generated": total_matches,
                    "players_participating": len(players_in_matches),
                    "participation_rate": f"{participation_rate:.2%}",
                    "generation_time_ms": round(generation_time * 1000, 2)
                })
            
            # Evaluate overall performance
            successful_scenarios = [r for r in scenario_results if r['success']]
            success = len(successful_scenarios) == len(test_scenarios)
            
            # Check if generation times are reasonable (< 2 seconds)
            if success:
                max_time = max(r['generation_time_ms'] for r in successful_scenarios)
                success = max_time < 2000  # 2 seconds
            
            details = {
                "scenarios_tested": len(test_scenarios),
                "scenarios_successful": len(successful_scenarios),
                "scenario_results": scenario_results
            }
            
            message = f"Successfully tested {len(successful_scenarios)}/{len(test_scenarios)} scenarios"
            
            self.log_result("Enhanced Algorithm Performance", success, message, details)
            
        except Exception as e:
            self.log_result("Enhanced Algorithm Performance", False, f"Exception: {str(e)}")
    
    def test_enhanced_shuffling_algorithm(self):
        """Test the enhanced_shuffle_with_rating_balance function effectiveness"""
        print("\n🔀 TEST 5: ENHANCED SHUFFLING ALGORITHM")
        
        try:
            # This test verifies that the enhanced shuffling creates better rating distribution
            # We'll test this by generating multiple rounds and checking rating spread
            
            # Reset and setup
            self.session.delete(f"{BACKEND_URL}/clear-all-data")
            self.session.post(f"{BACKEND_URL}/init")
            
            # Add players with very different ratings to test shuffling effectiveness
            diverse_players = [
                {"name": "HighRater1", "category": "Advanced"},  # Will get high rating
                {"name": "HighRater2", "category": "Advanced"},
                {"name": "MidRater1", "category": "Intermediate"},
                {"name": "MidRater2", "category": "Intermediate"},
                {"name": "LowRater1", "category": "Beginner"},
                {"name": "LowRater2", "category": "Beginner"},
                {"name": "HighRater3", "category": "Advanced"},
                {"name": "MidRater3", "category": "Intermediate"}
            ]
            
            for player_data in diverse_players:
                self.session.post(f"{BACKEND_URL}/players", json=player_data)
            
            # Generate multiple rounds to test shuffling
            rounds_data = []
            for round_num in range(1, 4):  # Test 3 rounds
                if round_num == 1:
                    response = self.session.post(f"{BACKEND_URL}/session/generate-matches")
                    if response.status_code == 200:
                        self.session.post(f"{BACKEND_URL}/session/start")
                else:
                    response = self.session.post(f"{BACKEND_URL}/session/next-round")
                
                if response.status_code != 200:
                    continue
                
                # Get matches for this round
                response = self.session.get(f"{BACKEND_URL}/matches")
                if response.status_code == 200:
                    all_matches = response.json()
                    round_matches = [m for m in all_matches if m['roundIndex'] == round_num]
                    rounds_data.append({
                        "round": round_num,
                        "matches": round_matches
                    })
            
            # Analyze shuffling effectiveness
            if len(rounds_data) >= 2:
                # Check if team compositions change between rounds
                round1_teams = set()
                round2_teams = set()
                
                for match in rounds_data[0]['matches']:
                    team_a = tuple(sorted(match['teamA']))
                    team_b = tuple(sorted(match['teamB']))
                    round1_teams.add(team_a)
                    round1_teams.add(team_b)
                
                for match in rounds_data[1]['matches']:
                    team_a = tuple(sorted(match['teamA']))
                    team_b = tuple(sorted(match['teamB']))
                    round2_teams.add(team_a)
                    round2_teams.add(team_b)
                
                # Calculate team variety
                common_teams = len(round1_teams & round2_teams)
                total_unique_teams = len(round1_teams | round2_teams)
                variety_score = 1.0 - (common_teams / total_unique_teams) if total_unique_teams > 0 else 0
                
                details = {
                    "rounds_tested": len(rounds_data),
                    "round1_teams": len(round1_teams),
                    "round2_teams": len(round2_teams),
                    "common_teams": common_teams,
                    "variety_score": f"{variety_score:.2%}"
                }
                
                success = variety_score > 0.5  # At least 50% team variety
                message = f"Team variety score: {variety_score:.2%}"
                
            else:
                success = False
                message = "Insufficient rounds generated for analysis"
                details = {"rounds_generated": len(rounds_data)}
            
            self.log_result("Enhanced Shuffling Algorithm", success, message, details)
            
        except Exception as e:
            self.log_result("Enhanced Shuffling Algorithm", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all enhanced reshuffling algorithm tests"""
        print("🏓 ENHANCED PLAYER RESHUFFLING ALGORITHM TEST SUITE")
        print("=" * 60)
        
        # Setup test environment
        if not self.setup_test_environment():
            print("❌ Failed to setup test environment. Aborting tests.")
            return
        
        # Run all tests
        self.test_basic_reshuffling_verification()
        self.test_rating_balance_verification()
        self.test_history_tracking_verification()
        self.test_enhanced_algorithm_performance()
        self.test_enhanced_shuffling_algorithm()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.test_results if r['success'])
        total = len(self.test_results)
        
        print(f"Tests Passed: {passed}/{total} ({passed/total:.1%})")
        print()
        
        for result in self.test_results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"{status}: {result['test']}")
            if not result['success']:
                print(f"   Error: {result['message']}")
        
        return passed == total

if __name__ == "__main__":
    tester = EnhancedReshufflingTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 ALL ENHANCED RESHUFFLING TESTS PASSED!")
    else:
        print("\n⚠️  SOME TESTS FAILED - CHECK RESULTS ABOVE")