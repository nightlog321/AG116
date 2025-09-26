#!/usr/bin/env python3
"""
Backend API Testing for Match Score Saving and Status Update Functionality
Focus: Testing match status changes from "pending" to "done" after scores are saved
"""

import asyncio
import json
import requests
import time
from typing import List, Dict, Any

# Get backend URL from environment
BACKEND_URL = "https://court-timer.preview.emergentagent.com/api"

class MatchScoreTestSuite:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_results = []
        self.created_players = []
        self.created_matches = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status}: {test_name}"
        if details:
            result += f" - {details}"
        print(result)
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        
    def make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make HTTP request to backend API"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == "GET":
                response = requests.get(url, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, timeout=10)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, timeout=10)
            elif method.upper() == "DELETE":
                response = requests.delete(url, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            # Check if response is JSON
            try:
                return {
                    "status_code": response.status_code,
                    "data": response.json(),
                    "success": response.status_code < 400
                }
            except json.JSONDecodeError:
                return {
                    "status_code": response.status_code,
                    "data": {"error": "Non-JSON response", "text": response.text[:500]},
                    "success": response.status_code < 400
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "status_code": 0,
                "data": {"error": str(e)},
                "success": False
            }
    
    def setup_test_data(self) -> bool:
        """Setup test data: players and matches"""
        print("\n🔧 SETTING UP TEST DATA...")
        
        # Step 1: Add test data (players)
        response = self.make_request("POST", "/add-test-data")
        if not response["success"]:
            self.log_test("Setup - Add Test Data", False, f"Failed to add test data: {response['data']}")
            return False
        
        self.log_test("Setup - Add Test Data", True, f"Added test players: {response['data'].get('message', 'Success')}")
        
        # Step 2: Generate matches
        response = self.make_request("POST", "/session/generate-matches")
        if not response["success"]:
            self.log_test("Setup - Generate Matches", False, f"Failed to generate matches: {response['data']}")
            return False
            
        self.log_test("Setup - Generate Matches", True, "Matches generated successfully")
        
        # Step 3: Get matches to verify they exist
        response = self.make_request("GET", "/matches")
        if not response["success"]:
            self.log_test("Setup - Get Matches", False, f"Failed to get matches: {response['data']}")
            return False
            
        matches = response["data"]
        if not matches:
            self.log_test("Setup - Get Matches", False, "No matches found after generation")
            return False
            
        self.created_matches = matches
        self.log_test("Setup - Get Matches", True, f"Found {len(matches)} matches")
        
        return True
    
    def test_score_saving_and_status_update(self) -> bool:
        """Test 1: Score Saving and Status Update"""
        print("\n🏓 TEST 1: SCORE SAVING AND STATUS UPDATE")
        
        if not self.created_matches:
            self.log_test("Test 1 - No Matches Available", False, "No matches available for testing")
            return False
        
        # Get first match
        match = self.created_matches[0]
        match_id = match["id"]
        
        # Verify initial status is "pending"
        if match["status"] != "pending":
            self.log_test("Test 1 - Initial Status Check", False, f"Expected 'pending', got '{match['status']}'")
            return False
        
        self.log_test("Test 1 - Initial Status Check", True, f"Match {match_id} has 'pending' status")
        
        # Save scores: scoreA=11, scoreB=7
        score_data = {"scoreA": 11, "scoreB": 7}
        response = self.make_request("PUT", f"/matches/{match_id}/score", score_data)
        
        if not response["success"]:
            self.log_test("Test 1 - Score Save API", False, f"Failed to save scores: {response['data']}")
            return False
        
        # Check response includes updated match with status="done"
        updated_match = response["data"]
        if updated_match["status"] != "done":
            self.log_test("Test 1 - Response Status Check", False, f"Expected 'done', got '{updated_match['status']}'")
            return False
        
        self.log_test("Test 1 - Response Status Check", True, "API response shows status='done'")
        
        # Verify scores are saved correctly
        if updated_match["scoreA"] != 11 or updated_match["scoreB"] != 7:
            self.log_test("Test 1 - Score Values Check", False, f"Expected scoreA=11, scoreB=7, got scoreA={updated_match['scoreA']}, scoreB={updated_match['scoreB']}")
            return False
        
        self.log_test("Test 1 - Score Values Check", True, "Scores saved correctly (11-7)")
        
        # Verify GET /api/matches reflects the status change
        response = self.make_request("GET", "/matches")
        if not response["success"]:
            self.log_test("Test 1 - GET Matches Verification", False, f"Failed to get matches: {response['data']}")
            return False
        
        # Find our updated match
        updated_matches = response["data"]
        our_match = next((m for m in updated_matches if m["id"] == match_id), None)
        
        if not our_match:
            self.log_test("Test 1 - Match Not Found", False, f"Match {match_id} not found in GET response")
            return False
        
        if our_match["status"] != "done":
            self.log_test("Test 1 - GET Status Verification", False, f"GET /matches shows status '{our_match['status']}', expected 'done'")
            return False
        
        self.log_test("Test 1 - GET Status Verification", True, "GET /matches confirms status='done'")
        
        return True
    
    def test_multiple_match_score_updates(self) -> bool:
        """Test 2: Multiple Match Score Updates"""
        print("\n🏓 TEST 2: MULTIPLE MATCH SCORE UPDATES")
        
        if len(self.created_matches) < 2:
            self.log_test("Test 2 - Insufficient Matches", False, f"Need at least 2 matches, found {len(self.created_matches)}")
            return False
        
        # Test scoring multiple matches independently
        test_scores = [
            {"scoreA": 15, "scoreB": 13},
            {"scoreA": 9, "scoreB": 11}
        ]
        
        scored_matches = []
        
        for i, match in enumerate(self.created_matches[:2]):  # Test first 2 matches
            match_id = match["id"]
            scores = test_scores[i]
            
            # Skip if already scored
            if match["status"] == "done":
                continue
            
            response = self.make_request("PUT", f"/matches/{match_id}/score", scores)
            
            if not response["success"]:
                self.log_test(f"Test 2 - Score Match {i+1}", False, f"Failed to score match {match_id}: {response['data']}")
                continue
            
            updated_match = response["data"]
            if updated_match["status"] != "done":
                self.log_test(f"Test 2 - Status Match {i+1}", False, f"Match {match_id} status is '{updated_match['status']}', expected 'done'")
                continue
            
            scored_matches.append({
                "id": match_id,
                "scoreA": scores["scoreA"],
                "scoreB": scores["scoreB"]
            })
            
            self.log_test(f"Test 2 - Score Match {i+1}", True, f"Match {match_id} scored {scores['scoreA']}-{scores['scoreB']}, status='done'")
        
        if not scored_matches:
            self.log_test("Test 2 - No Matches Scored", False, "No matches were successfully scored")
            return False
        
        # Verify only scored matches changed status
        response = self.make_request("GET", "/matches")
        if not response["success"]:
            self.log_test("Test 2 - GET Matches Check", False, f"Failed to get matches: {response['data']}")
            return False
        
        all_matches = response["data"]
        scored_ids = {m["id"] for m in scored_matches}
        
        done_count = 0
        pending_count = 0
        
        for match in all_matches:
            if match["id"] in scored_ids:
                if match["status"] != "done":
                    self.log_test("Test 2 - Scored Match Status", False, f"Scored match {match['id']} has status '{match['status']}', expected 'done'")
                    return False
                done_count += 1
            else:
                if match["status"] == "pending":
                    pending_count += 1
        
        self.log_test("Test 2 - Independent Updates", True, f"{done_count} matches scored independently, {pending_count} remain pending")
        
        return True
    
    def test_score_api_response_verification(self) -> bool:
        """Test 3: Score API Response Verification"""
        print("\n🏓 TEST 3: SCORE API RESPONSE VERIFICATION")
        
        # Find a pending match to test
        pending_match = None
        for match in self.created_matches:
            if match["status"] == "pending":
                pending_match = match
                break
        
        if not pending_match:
            self.log_test("Test 3 - No Pending Match", False, "No pending matches available for testing")
            return False
        
        match_id = pending_match["id"]
        test_scores = {"scoreA": 21, "scoreB": 19}
        
        response = self.make_request("PUT", f"/matches/{match_id}/score", test_scores)
        
        if not response["success"]:
            self.log_test("Test 3 - API Call", False, f"Score API failed: {response['data']}")
            return False
        
        self.log_test("Test 3 - API Call", True, "Score API call successful")
        
        # Verify response body structure
        match_data = response["data"]
        required_fields = ["id", "status", "scoreA", "scoreB", "teamA", "teamB", "matchType", "category", "roundIndex", "courtIndex"]
        
        missing_fields = []
        for field in required_fields:
            if field not in match_data:
                missing_fields.append(field)
        
        if missing_fields:
            self.log_test("Test 3 - Response Structure", False, f"Missing fields: {missing_fields}")
            return False
        
        self.log_test("Test 3 - Response Structure", True, "Response includes all required Match model fields")
        
        # Verify specific values
        if match_data["status"] != "done":
            self.log_test("Test 3 - Status in Response", False, f"Status is '{match_data['status']}', expected 'done'")
            return False
        
        if match_data["scoreA"] != test_scores["scoreA"] or match_data["scoreB"] != test_scores["scoreB"]:
            self.log_test("Test 3 - Scores in Response", False, f"Scores don't match: expected {test_scores}, got scoreA={match_data['scoreA']}, scoreB={match_data['scoreB']}")
            return False
        
        self.log_test("Test 3 - Response Values", True, f"Response correctly shows status='done', scores={test_scores['scoreA']}-{test_scores['scoreB']}")
        
        return True
    
    def test_player_statistics_update(self) -> bool:
        """Test 4: Player Statistics Update"""
        print("\n🏓 TEST 4: PLAYER STATISTICS UPDATE")
        
        # Get initial player stats
        response = self.make_request("GET", "/players")
        if not response["success"]:
            self.log_test("Test 4 - Get Initial Stats", False, f"Failed to get players: {response['data']}")
            return False
        
        initial_players = {p["id"]: p for p in response["data"]}
        
        # Find a pending match to score
        pending_match = None
        for match in self.created_matches:
            if match["status"] == "pending":
                pending_match = match
                break
        
        if not pending_match:
            self.log_test("Test 4 - No Pending Match", False, "No pending matches available for testing")
            return False
        
        match_id = pending_match["id"]
        team_a_ids = pending_match["teamA"]
        team_b_ids = pending_match["teamB"]
        
        # Score the match (Team A wins)
        test_scores = {"scoreA": 15, "scoreB": 10}
        response = self.make_request("PUT", f"/matches/{match_id}/score", test_scores)
        
        if not response["success"]:
            self.log_test("Test 4 - Score Match", False, f"Failed to score match: {response['data']}")
            return False
        
        self.log_test("Test 4 - Score Match", True, f"Match scored {test_scores['scoreA']}-{test_scores['scoreB']}")
        
        # Get updated player stats
        response = self.make_request("GET", "/players")
        if not response["success"]:
            self.log_test("Test 4 - Get Updated Stats", False, f"Failed to get updated players: {response['data']}")
            return False
        
        updated_players = {p["id"]: p for p in response["data"]}
        
        # Verify winner stats (Team A)
        winners_updated = 0
        for player_id in team_a_ids:
            if player_id not in initial_players or player_id not in updated_players:
                continue
                
            initial = initial_players[player_id]
            updated = updated_players[player_id]
            
            # Check wins increased by 1
            if updated["wins"] != initial["wins"] + 1:
                self.log_test("Test 4 - Winner Wins Update", False, f"Player {player_id} wins: expected {initial['wins'] + 1}, got {updated['wins']}")
                return False
            
            # Check point differential increased
            point_diff_increase = test_scores["scoreA"] - test_scores["scoreB"]
            expected_point_diff = initial["stats"]["pointDiff"] + point_diff_increase
            if updated["stats"]["pointDiff"] != expected_point_diff:
                self.log_test("Test 4 - Winner Point Diff", False, f"Player {player_id} pointDiff: expected {expected_point_diff}, got {updated['stats']['pointDiff']}")
                return False
            
            winners_updated += 1
        
        # Verify loser stats (Team B)
        losers_updated = 0
        for player_id in team_b_ids:
            if player_id not in initial_players or player_id not in updated_players:
                continue
                
            initial = initial_players[player_id]
            updated = updated_players[player_id]
            
            # Check losses increased by 1
            if updated["losses"] != initial["losses"] + 1:
                self.log_test("Test 4 - Loser Losses Update", False, f"Player {player_id} losses: expected {initial['losses'] + 1}, got {updated['losses']}")
                return False
            
            # Check point differential decreased
            point_diff_decrease = test_scores["scoreA"] - test_scores["scoreB"]
            expected_point_diff = initial["stats"]["pointDiff"] - point_diff_decrease
            if updated["stats"]["pointDiff"] != expected_point_diff:
                self.log_test("Test 4 - Loser Point Diff", False, f"Player {player_id} pointDiff: expected {expected_point_diff}, got {updated['stats']['pointDiff']}")
                return False
            
            losers_updated += 1
        
        if winners_updated == 0 and losers_updated == 0:
            self.log_test("Test 4 - No Stats Updated", False, "No player statistics were updated")
            return False
        
        self.log_test("Test 4 - Player Stats Update", True, f"Updated stats for {winners_updated} winners and {losers_updated} losers")
        
        return True
    
    def run_all_tests(self):
        """Run all test scenarios"""
        print("🚀 STARTING MATCH SCORE SAVING AND STATUS UPDATE TESTS")
        print("=" * 60)
        
        # Setup test data
        if not self.setup_test_data():
            print("\n❌ SETUP FAILED - Cannot proceed with tests")
            return
        
        # Run all tests
        test_methods = [
            self.test_score_saving_and_status_update,
            self.test_multiple_match_score_updates,
            self.test_score_api_response_verification,
            self.test_player_statistics_update
        ]
        
        passed_tests = 0
        total_tests = len(test_methods)
        
        for test_method in test_methods:
            try:
                if test_method():
                    passed_tests += 1
            except Exception as e:
                self.log_test(f"{test_method.__name__}", False, f"Exception: {str(e)}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("🏁 TEST SUMMARY")
        print("=" * 60)
        
        success_rate = (passed_tests / total_tests) * 100
        print(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        if success_rate == 100:
            print("🎉 ALL TESTS PASSED! Match score saving and status update functionality is working perfectly!")
        elif success_rate >= 75:
            print("✅ Most tests passed. Minor issues may need attention.")
        else:
            print("❌ Multiple test failures detected. Significant issues need to be resolved.")
        
        # Print detailed results
        print("\nDetailed Results:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['test']}")
            if result["details"]:
                print(f"   └─ {result['details']}")

def main():
    """Main test execution"""
    test_suite = MatchScoreTestSuite()
    test_suite.run_all_tests()

if __name__ == "__main__":
    main()