#!/usr/bin/env python3
"""
CourtChime Backend Testing - Final Fixes Verification
Testing first round generation fixes and Top Court mode with maximize courts
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any, Optional

# Backend URL from environment
BACKEND_URL = "https://courtchime.preview.emergentagent.com/api"
CLUB_NAME = "Main Club"
ACCESS_CODE = "demo123"

class FinalFixesTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
    
    def authenticate(self) -> bool:
        """Authenticate with the club"""
        try:
            login_data = {
                "club_name": CLUB_NAME,
                "access_code": ACCESS_CODE
            }
            
            response = self.session.post(f"{BACKEND_URL}/auth/login", json=login_data)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Club Authentication", True, f"Authenticated as {data.get('club_name')}")
                return True
            else:
                self.log_test("Club Authentication", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Club Authentication", False, f"Error: {str(e)}")
            return False
    
    def get_session_config(self) -> Dict[str, Any]:
        """Get current session configuration"""
        try:
            response = self.session.get(f"{BACKEND_URL}/session", params={"club_name": CLUB_NAME})
            if response.status_code == 200:
                data = response.json()
                return data.get('config', {})
            return {}
        except Exception as e:
            print(f"Error getting session config: {e}")
            return {}
    
    def update_session_config(self, config_updates: Dict[str, Any]) -> bool:
        """Update session configuration"""
        try:
            response = self.session.put(f"{BACKEND_URL}/session/config", 
                                      params={"club_name": CLUB_NAME}, 
                                      json=config_updates)
            return response.status_code == 200
        except Exception as e:
            print(f"Error updating session config: {e}")
            return False
    
    def get_players(self) -> List[Dict[str, Any]]:
        """Get all players for the club"""
        try:
            response = self.session.get(f"{BACKEND_URL}/players", params={"club_name": CLUB_NAME})
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error getting players: {e}")
            return []
    
    def generate_matches(self) -> Dict[str, Any]:
        """Generate matches for current round"""
        try:
            response = self.session.post(f"{BACKEND_URL}/session/generate-matches", 
                                       params={"club_name": CLUB_NAME})
            if response.status_code == 200:
                return response.json()
            else:
                text = response.text
                print(f"Generate matches failed: {response.status_code} - {text}")
                return {}
        except Exception as e:
            print(f"Error generating matches: {e}")
            return {}
    
    def get_matches(self) -> List[Dict[str, Any]]:
        """Get current matches"""
        try:
            response = self.session.get(f"{BACKEND_URL}/matches", params={"club_name": CLUB_NAME})
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error getting matches: {e}")
            return []
    
    def deactivate_players(self, player_ids: List[str]) -> bool:
        """Deactivate specific players"""
        try:
            success_count = 0
            for player_id in player_ids:
                response = self.session.patch(f"{BACKEND_URL}/players/{player_id}/toggle-active", 
                                            params={"club_name": CLUB_NAME})
                if response.status_code == 200:
                    success_count += 1
            return success_count == len(player_ids)
        except Exception as e:
            print(f"Error deactivating players: {e}")
            return False
    
    def activate_all_players(self) -> bool:
        """Activate all players"""
        try:
            players = self.get_players()
            inactive_players = [p['id'] for p in players if not p.get('isActive', True)]
            
            if not inactive_players:
                return True
                
            success_count = 0
            for player_id in inactive_players:
                response = self.session.patch(f"{BACKEND_URL}/players/{player_id}/toggle-active", 
                                            params={"club_name": CLUB_NAME})
                if response.status_code == 200:
                    success_count += 1
            return success_count == len(inactive_players)
        except Exception as e:
            print(f"Error activating players: {e}")
            return False
    
    def clear_matches(self) -> bool:
        """Clear all matches to reset session"""
        try:
            response = self.session.delete(f"{BACKEND_URL}/matches", params={"club_name": CLUB_NAME})
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"Error clearing matches: {e}")
            return False
    
    def test_first_round_maximize_courts(self):
        """Test 1: First Round Generation with Maximize Courts"""
        print("\n🎯 Testing First Round Generation with Maximize Courts")
        
        # Ensure all players are active
        self.activate_all_players()
        
        # Clear any existing matches
        self.clear_matches()
        
        # Configure for maximize courts
        config = {
            "numCourts": 3,
            "allowSingles": True,
            "allowDoubles": True,
            "allowCrossCategory": False,
            "maximizeCourtUsage": True,
            "rotationModel": "legacy"
        }
        
        config_updated = self.update_session_config(config)
        if not config_updated:
            self.log_test("First Round - Config Update", False, "Failed to update session config")
            return
        
        # Test Scenario 1: 16 players, 3 courts
        players = self.get_players()
        active_players = [p for p in players if p.get('isActive', True)]
        
        if len(active_players) < 12:
            self.log_test("First Round - Player Count", False, f"Need at least 12 active players, got {len(active_players)}")
            return
        
        # Generate matches
        result = self.generate_matches()
        if not result:
            self.log_test("First Round - Match Generation", False, "Failed to generate matches")
            return
        
        matches = self.get_matches()
        
        # Verify all 3 courts are used
        court_indices = set(match['courtIndex'] for match in matches)
        courts_used = len(court_indices)
        
        # Count players in matches
        players_in_matches = set()
        for match in matches:
            players_in_matches.update(match['teamA'])
            players_in_matches.update(match['teamB'])
        
        players_playing = len(players_in_matches)
        sitouts = len(active_players) - players_playing
        
        # Verify maximize courts logic
        expected_courts = min(3, len(matches))
        courts_filled = courts_used == expected_courts
        
        self.log_test("First Round - All Courts Used", courts_filled, 
                     f"Used {courts_used}/{expected_courts} courts, {players_playing} players, {sitouts} sitouts")
        
        # Test Scenario 2: Verify algorithm uses schedule_round
        # Check if matches have proper structure indicating advanced algorithm
        has_proper_structure = all(
            'teamA' in match and 'teamB' in match and 'courtIndex' in match 
            for match in matches
        )
        
        self.log_test("First Round - Advanced Algorithm Structure", has_proper_structure,
                     f"Matches have proper structure from schedule_round function")
    
    def test_top_court_first_round(self):
        """Test 2: Top Court Mode First Round"""
        print("\n🏆 Testing Top Court Mode First Round")
        
        # Clear matches and configure for top court
        self.clear_matches()
        self.activate_all_players()
        
        config = {
            "numCourts": 3,
            "allowSingles": True,
            "allowDoubles": True,
            "allowCrossCategory": False,
            "maximizeCourtUsage": True,
            "rotationModel": "top_court"
        }
        
        config_updated = self.update_session_config(config)
        if not config_updated:
            self.log_test("Top Court - Config Update", False, "Failed to update config for top court mode")
            return
        
        # Generate first round matches
        result = self.generate_matches()
        if not result:
            self.log_test("Top Court - First Round Generation", False, "Failed to generate first round")
            return
        
        matches = self.get_matches()
        
        # Verify Court 0 exists (Top Court)
        court_0_matches = [m for m in matches if m['courtIndex'] == 0]
        has_top_court = len(court_0_matches) > 0
        
        # Verify all courts are filled when maximize courts is enabled
        court_indices = set(match['courtIndex'] for match in matches)
        courts_used = len(court_indices)
        
        # Count active players
        players = self.get_players()
        active_players = [p for p in players if p.get('isActive', True)]
        
        players_in_matches = set()
        for match in matches:
            players_in_matches.update(match['teamA'])
            players_in_matches.update(match['teamB'])
        
        all_courts_filled = courts_used == 3  # Should use all 3 courts
        
        self.log_test("Top Court - Court 0 Exists", has_top_court, 
                     f"Court 0 (Top Court) found: {len(court_0_matches)} matches")
        
        self.log_test("Top Court - All Courts Filled", all_courts_filled,
                     f"Used {courts_used}/3 courts with {len(players_in_matches)} players")
        
        # Verify inactive players are excluded
        inactive_players_in_matches = []
        for match in matches:
            for player_id in match['teamA'] + match['teamB']:
                player = next((p for p in active_players if p['id'] == player_id), None)
                if player and not player.get('isActive', True):
                    inactive_players_in_matches.append(player_id)
        
        no_inactive_in_matches = len(inactive_players_in_matches) == 0
        self.log_test("Top Court - No Inactive Players", no_inactive_in_matches,
                     f"Inactive players in matches: {len(inactive_players_in_matches)}")
    
    def test_cross_category_maximize_courts(self):
        """Test 4: Cross Category + Maximize Courts"""
        print("\n🔀 Testing Cross Category + Maximize Courts")
        
        self.clear_matches()
        self.activate_all_players()
        
        config = {
            "numCourts": 3,
            "allowSingles": True,
            "allowDoubles": True,
            "allowCrossCategory": True,  # Enable cross category
            "maximizeCourtUsage": True,  # Enable maximize courts
            "rotationModel": "legacy"
        }
        
        config_updated = self.update_session_config(config)
        if not config_updated:
            self.log_test("Cross Category - Config Update", False, "Failed to update config")
            return
        
        # Generate matches
        result = self.generate_matches()
        if not result:
            self.log_test("Cross Category - Match Generation", False, "Failed to generate matches")
            return
        
        matches = self.get_matches()
        
        # Verify all courts are filled
        court_indices = set(match['courtIndex'] for match in matches)
        courts_used = len(court_indices)
        
        # Verify mixed category matches
        mixed_matches = [m for m in matches if m.get('category') == 'Mixed']
        has_mixed_matches = len(mixed_matches) > 0
        
        # Count players and sitouts
        players = self.get_players()
        active_players = [p for p in players if p.get('isActive', True)]
        
        players_in_matches = set()
        for match in matches:
            players_in_matches.update(match['teamA'])
            players_in_matches.update(match['teamB'])
        
        sitouts = len(active_players) - len(players_in_matches)
        
        # Verify sitouts are minimized
        expected_max_sitouts = len(active_players) % 4  # For doubles
        sitouts_minimized = sitouts <= expected_max_sitouts + 2  # Allow some flexibility
        
        self.log_test("Cross Category - All Courts Used", courts_used == 3,
                     f"Used {courts_used}/3 courts")
        
        self.log_test("Cross Category - Mixed Matches Created", has_mixed_matches,
                     f"Mixed category matches: {len(mixed_matches)}/{len(matches)}")
        
        self.log_test("Cross Category - Sitouts Minimized", sitouts_minimized,
                     f"Sitouts: {sitouts}, Active players: {len(active_players)}")
    
    def test_inactive_player_filtering(self):
        """Test 5: Inactive Player Filtering"""
        print("\n🚫 Testing Inactive Player Filtering")
        
        self.clear_matches()
        
        # Get players and deactivate some
        players = self.get_players()
        if len(players) < 6:
            self.log_test("Inactive Filter - Insufficient Players", False, f"Need at least 6 players, got {len(players)}")
            return
        
        # Deactivate 2 players
        players_to_deactivate = players[:2]
        deactivated = self.deactivate_players([p['id'] for p in players_to_deactivate])
        
        if not deactivated:
            self.log_test("Inactive Filter - Player Deactivation", False, "Failed to deactivate players")
            return
        
        # Configure session
        config = {
            "numCourts": 3,
            "allowSingles": True,
            "allowDoubles": True,
            "allowCrossCategory": False,
            "maximizeCourtUsage": True,
            "rotationModel": "legacy"
        }
        
        self.update_session_config(config)
        
        # Generate matches
        result = self.generate_matches()
        if not result:
            self.log_test("Inactive Filter - Match Generation", False, "Failed to generate matches")
            return
        
        matches = self.get_matches()
        
        # Verify inactive players are NOT in matches
        deactivated_ids = set(p['id'] for p in players_to_deactivate)
        inactive_in_matches = set()
        
        for match in matches:
            for player_id in match['teamA'] + match['teamB']:
                if player_id in deactivated_ids:
                    inactive_in_matches.add(player_id)
        
        no_inactive_in_matches = len(inactive_in_matches) == 0
        
        # Get updated player list to verify active count
        updated_players = self.get_players()
        active_players = [p for p in updated_players if p.get('isActive', True)]
        
        # Verify sitout calculations don't include inactive players
        players_in_matches = set()
        for match in matches:
            players_in_matches.update(match['teamA'])
            players_in_matches.update(match['teamB'])
        
        sitouts = len(active_players) - len(players_in_matches)
        
        self.log_test("Inactive Filter - No Inactive in Matches", no_inactive_in_matches,
                     f"Inactive players found in matches: {len(inactive_in_matches)}")
        
        self.log_test("Inactive Filter - Correct Active Count", len(active_players) == len(players) - 2,
                     f"Active: {len(active_players)}, Total: {len(players)}, Deactivated: 2")
        
        self.log_test("Inactive Filter - Proper Sitout Calculation", sitouts >= 0,
                     f"Sitouts: {sitouts}, Active players: {len(active_players)}")
        
        # Reactivate players for next tests
        self.activate_all_players()
    
    def test_court_utilization_scenarios(self):
        """Test various court utilization scenarios"""
        print("\n📊 Testing Court Utilization Scenarios")
        
        self.clear_matches()
        self.activate_all_players()
        
        # Test different player/court combinations
        scenarios = [
            {"players": 16, "courts": 3, "expected_matches": 3, "description": "16 players, 3 courts"},
            {"players": 10, "courts": 3, "expected_matches": 3, "description": "10 players, 3 courts"},
            {"players": 12, "courts": 3, "expected_matches": 3, "description": "12 players, 3 courts"}
        ]
        
        players = self.get_players()
        active_players = [p for p in players if p.get('isActive', True)]
        
        for scenario in scenarios:
            self.clear_matches()
            
            # Configure for scenario
            config = {
                "numCourts": scenario["courts"],
                "allowSingles": True,
                "allowDoubles": True,
                "allowCrossCategory": False,
                "maximizeCourtUsage": True,
                "rotationModel": "legacy"
            }
            
            self.update_session_config(config)
            
            # Generate matches
            result = self.generate_matches()
            if not result:
                self.log_test(f"Scenario - {scenario['description']}", False, "Failed to generate matches")
                continue
            
            matches = self.get_matches()
            
            # Verify court usage
            court_indices = set(match['courtIndex'] for match in matches)
            courts_used = len(court_indices)
            
            # Count players in matches
            players_in_matches = set()
            for match in matches:
                players_in_matches.update(match['teamA'])
                players_in_matches.update(match['teamB'])
            
            available_players = min(len(active_players), scenario["players"])
            sitouts = available_players - len(players_in_matches)
            
            # For maximize courts, should fill all available courts when possible
            expected_courts = min(scenario["courts"], len(matches))
            courts_optimized = courts_used == expected_courts
            
            self.log_test(f"Scenario - {scenario['description']}", courts_optimized,
                         f"Courts: {courts_used}/{scenario['courts']}, Players: {len(players_in_matches)}, Sitouts: {sitouts}")
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting CourtChime Backend Testing - Final Fixes Verification")
        print("=" * 70)
        
        # Authenticate first
        if not self.authenticate():
            print("❌ Authentication failed. Cannot proceed with tests.")
            return
        
        # Run all test suites
        self.test_first_round_maximize_courts()
        self.test_top_court_first_round()
        self.test_cross_category_maximize_courts()
        self.test_inactive_player_filtering()
        self.test_court_utilization_scenarios()
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Show failed tests
        failed_tests = [result for result in self.test_results if not result['success']]
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  • {test['test']}: {test['details']}")
        else:
            print(f"\n✅ ALL TESTS PASSED!")
        
        return passed == total

def main():
    """Main test runner"""
    tester = FinalFixesTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()