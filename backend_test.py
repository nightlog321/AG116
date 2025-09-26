#!/usr/bin/env python3
"""
CourtChime Comprehensive Pre-Deployment Testing Suite
====================================================

This test suite performs comprehensive testing of all CourtChime backend APIs
to ensure production readiness before deployment.

Test Categories:
1. Database Initialization & Setup
2. Player Management System
3. Session Management & Configuration
4. Match Generation & Court Assignment
5. Session Flow & Phase Transitions
6. Score Management & Status Updates
7. Round Progression System
8. Enhanced Features Validation
9. Error Handling & Edge Cases
10. Performance & Load Testing
"""

import requests
import json
import time
import uuid
from typing import Dict, List, Any, Optional
import sys
from datetime import datetime

# Configuration
BACKEND_URL = "https://court-timer.preview.emergentagent.com/api"
TIMEOUT = 30
MAX_RETRIES = 3

class CourtChimeTestSuite:
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = TIMEOUT
        self.test_results = []
        self.test_players = []
        self.test_matches = []
        self.session_id = None
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_time: float = 0):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "success": success,
            "details": details,
            "response_time": f"{response_time:.3f}s" if response_time > 0 else "N/A",
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{status} | {test_name} | {details} | {result['response_time']}")
        
    def make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> tuple:
        """Make HTTP request with error handling and timing"""
        url = f"{BACKEND_URL}{endpoint}"
        start_time = time.time()
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, params=params)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, params=params)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response_time = time.time() - start_time
            
            # Try to parse JSON response
            try:
                json_data = response.json()
            except:
                json_data = {"raw_response": response.text}
                
            return response.status_code, json_data, response_time
            
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            return 0, {"error": str(e)}, response_time

    # ========================================
    # 1. Database Initialization & Setup Tests
    # ========================================
    
    def test_database_initialization(self):
        """Test database initialization and default setup"""
        print("\n🔧 TESTING DATABASE INITIALIZATION & SETUP")
        
        # Test 1.1: Initialize default categories and session
        status_code, response, response_time = self.make_request("POST", "/init")
        success = status_code == 200 and "message" in response
        self.log_test("Database Initialization", success, 
                     f"Status: {status_code}, Response: {response.get('message', 'No message')}", response_time)
        
        # Test 1.2: Verify default categories created
        status_code, response, response_time = self.make_request("GET", "/categories")
        success = status_code == 200 and isinstance(response, list) and len(response) >= 3
        categories = [cat.get('name', '') for cat in response] if isinstance(response, list) else []
        expected_categories = ['Beginner', 'Intermediate', 'Advanced']
        has_defaults = all(cat in categories for cat in expected_categories)
        self.log_test("Default Categories Verification", success and has_defaults,
                     f"Found categories: {categories}", response_time)
        
        # Test 1.3: Verify session initialized properly
        status_code, response, response_time = self.make_request("GET", "/session")
        success = status_code == 200 and "id" in response and "phase" in response
        session_phase = response.get("phase", "unknown") if isinstance(response, dict) else "unknown"
        self.session_id = response.get("id") if isinstance(response, dict) else None
        self.log_test("Session Initialization", success,
                     f"Session phase: {session_phase}, ID: {self.session_id}", response_time)
        
        # Test 1.4: Verify SQLite database working
        status_code, response, response_time = self.make_request("GET", "/sqlite/players")
        success = status_code == 200 and isinstance(response, list)
        self.log_test("SQLite Database Connectivity", success,
                     f"SQLite players endpoint accessible, returned {len(response) if isinstance(response, list) else 0} players", response_time)

    # ========================================
    # 2. Player Management System Tests
    # ========================================
    
    def test_player_management(self):
        """Test comprehensive player management operations"""
        print("\n👥 TESTING PLAYER MANAGEMENT SYSTEM")
        
        # Test 2.1: Add test data (multiple players with different categories)
        status_code, response, response_time = self.make_request("POST", "/add-test-data")
        success = status_code == 200 and "message" in response
        self.log_test("Add Test Players", success,
                     f"Status: {status_code}, Message: {response.get('message', 'No message')}", response_time)
        
        # Test 2.2: Retrieve all players
        status_code, response, response_time = self.make_request("GET", "/players")
        success = status_code == 200 and isinstance(response, list) and len(response) > 0
        self.test_players = response if isinstance(response, list) else []
        player_count = len(self.test_players)
        categories_found = set(p.get('category', '') for p in self.test_players)
        self.log_test("Retrieve All Players", success,
                     f"Found {player_count} players across categories: {list(categories_found)}", response_time)
        
        # Test 2.3: Create individual player
        if self.test_players:
            new_player_data = {
                "name": f"Test Player {uuid.uuid4().hex[:8]}",
                "category": "Intermediate"
            }
            status_code, response, response_time = self.make_request("POST", "/players", new_player_data)
            success = status_code == 200 and "id" in response and response.get("name") == new_player_data["name"]
            created_player_id = response.get("id") if isinstance(response, dict) else None
            self.log_test("Create Individual Player", success,
                         f"Created player: {response.get('name', 'Unknown')} with ID: {created_player_id}", response_time)
            
            # Test 2.4: Update player
            if created_player_id:
                update_data = {"name": f"Updated Player {uuid.uuid4().hex[:8]}", "category": "Advanced"}
                status_code, response, response_time = self.make_request("PUT", f"/players/{created_player_id}", update_data)
                success = status_code == 200 and response.get("name") == update_data["name"]
                self.log_test("Update Player", success,
                             f"Updated to: {response.get('name', 'Unknown')}, Category: {response.get('category', 'Unknown')}", response_time)
                
                # Test 2.5: Delete player
                status_code, response, response_time = self.make_request("DELETE", f"/players/{created_player_id}")
                success = status_code == 200 and "message" in response
                self.log_test("Delete Player", success,
                             f"Deletion message: {response.get('message', 'No message')}", response_time)

    # ========================================
    # 3. Session Management & Configuration Tests
    # ========================================
    
    def test_session_management(self):
        """Test session management and configuration operations"""
        print("\n⚙️ TESTING SESSION MANAGEMENT & CONFIGURATION")
        
        # Test 3.1: Get session configuration
        status_code, response, response_time = self.make_request("GET", "/session")
        success = status_code == 200 and "config" in response
        config = response.get("config", {}) if isinstance(response, dict) else {}
        self.log_test("Get Session Configuration", success,
                     f"Config fields: {list(config.keys()) if config else 'None'}", response_time)
        
        # Test 3.2: Update session configuration
        new_config = {
            "numCourts": 6,
            "playSeconds": 900,  # 15 minutes
            "bufferSeconds": 45,
            "allowSingles": True,
            "allowDoubles": True,
            "allowCrossCategory": False,
            "maximizeCourtUsage": True
        }
        status_code, response, response_time = self.make_request("PUT", "/session/config", new_config)
        success = status_code == 200
        self.log_test("Update Session Configuration", success,
                     f"Updated config with {len(new_config)} fields", response_time)
        
        # Test 3.3: Verify configuration persistence
        status_code, response, response_time = self.make_request("GET", "/session")
        success = status_code == 200 and "config" in response
        updated_config = response.get("config", {}) if isinstance(response, dict) else {}
        config_match = updated_config.get("numCourts") == 6 and updated_config.get("playSeconds") == 900
        self.log_test("Configuration Persistence", success and config_match,
                     f"Courts: {updated_config.get('numCourts')}, PlayTime: {updated_config.get('playSeconds')}s", response_time)
        
        # Test 3.4: Session reset functionality
        status_code, response, response_time = self.make_request("POST", "/session/reset")
        success = status_code == 200
        self.log_test("Session Reset", success,
                     f"Reset response: {response.get('message', 'No message') if isinstance(response, dict) else response}", response_time)

    # ========================================
    # 4. Match Generation & Court Assignment Tests
    # ========================================
    
    def test_match_generation(self):
        """Test match generation and court assignment functionality"""
        print("\n🏓 TESTING MATCH GENERATION & COURT ASSIGNMENT")
        
        # Test 4.1: Generate matches
        status_code, response, response_time = self.make_request("POST", "/session/generate-matches")
        success = status_code == 200
        self.log_test("Generate Matches", success,
                     f"Match generation response: {response.get('message', 'No message') if isinstance(response, dict) else 'Success'}", response_time)
        
        # Test 4.2: Retrieve generated matches
        status_code, response, response_time = self.make_request("GET", "/matches")
        success = status_code == 200 and isinstance(response, list)
        self.test_matches = response if isinstance(response, list) else []
        match_count = len(self.test_matches)
        self.log_test("Retrieve Generated Matches", success,
                     f"Found {match_count} matches", response_time)
        
        # Test 4.3: Verify match structure and court assignments
        if self.test_matches:
            match = self.test_matches[0]
            required_fields = ['id', 'roundIndex', 'courtIndex', 'category', 'teamA', 'teamB', 'status', 'matchType']
            has_required_fields = all(field in match for field in required_fields)
            has_proper_teams = isinstance(match.get('teamA'), list) and isinstance(match.get('teamB'), list)
            has_court_assignment = isinstance(match.get('courtIndex'), int) and match.get('courtIndex') >= 0
            
            success = has_required_fields and has_proper_teams and has_court_assignment
            self.log_test("Match Structure Validation", success,
                         f"Court: {match.get('courtIndex')}, Teams: {len(match.get('teamA', []))}v{len(match.get('teamB', []))}, Type: {match.get('matchType')}", response_time)
        
        # Test 4.4: Verify category-based assignments
        if self.test_matches:
            categories_in_matches = set(match.get('category', '') for match in self.test_matches)
            success = len(categories_in_matches) > 0
            self.log_test("Category-Based Assignments", success,
                         f"Match categories: {list(categories_in_matches)}", response_time)
        
        # Test 4.5: Test with different player configurations
        # Update config for mixed testing
        mixed_config = {"allowCrossCategory": True, "maximizeCourtUsage": True}
        status_code, response, response_time = self.make_request("PUT", "/session/config", mixed_config)
        
        # Generate matches with cross-category enabled
        status_code, response, response_time = self.make_request("POST", "/session/generate-matches")
        success = status_code == 200
        self.log_test("Cross-Category Match Generation", success,
                     f"Mixed category generation: {response.get('message', 'Success') if isinstance(response, dict) else 'Success'}", response_time)

    # ========================================
    # 5. Session Flow & Phase Transitions Tests
    # ========================================
    
    def test_session_flow(self):
        """Test session flow and phase transitions"""
        print("\n🔄 TESTING SESSION FLOW & PHASE TRANSITIONS")
        
        # Test 5.1: Start session (idle -> play)
        status_code, response, response_time = self.make_request("POST", "/session/start")
        success = status_code == 200
        self.log_test("Start Session (Play Phase)", success,
                     f"Session start response: {response.get('message', 'Success') if isinstance(response, dict) else 'Success'}", response_time)
        
        # Verify session is in play phase
        status_code, response, response_time = self.make_request("GET", "/session")
        success = status_code == 200 and response.get("phase") == "play"
        current_round = response.get("currentRound", 0) if isinstance(response, dict) else 0
        time_remaining = response.get("timeRemaining", 0) if isinstance(response, dict) else 0
        self.log_test("Verify Play Phase", success,
                     f"Phase: {response.get('phase')}, Round: {current_round}, Time: {time_remaining}s", response_time)
        
        # Test 5.2: Pause session
        status_code, response, response_time = self.make_request("POST", "/session/pause")
        success = status_code == 200
        self.log_test("Pause Session", success,
                     f"Pause response: {response.get('message', 'Success') if isinstance(response, dict) else 'Success'}", response_time)
        
        # Test 5.3: Resume session
        status_code, response, response_time = self.make_request("POST", "/session/resume")
        success = status_code == 200
        self.log_test("Resume Session", success,
                     f"Resume response: {response.get('message', 'Success') if isinstance(response, dict) else 'Success'}", response_time)
        
        # Test 5.4: Buffer phase transition
        status_code, response, response_time = self.make_request("POST", "/session/buffer")
        success = status_code == 200
        self.log_test("Buffer Phase Transition", success,
                     f"Buffer response: {response.get('message', 'Success') if isinstance(response, dict) else 'Success'}", response_time)
        
        # Test 5.5: Horn functionality
        status_code, response, response_time = self.make_request("POST", "/session/horn")
        success = status_code == 200
        horn_type = response.get("hornType", "unknown") if isinstance(response, dict) else "unknown"
        self.log_test("Horn Functionality", success,
                     f"Horn type: {horn_type}, Response: {response.get('message', 'Success') if isinstance(response, dict) else 'Success'}", response_time)

    # ========================================
    # 6. Score Management & Status Updates Tests
    # ========================================
    
    def test_score_management(self):
        """Test score management and match status updates"""
        print("\n🏆 TESTING SCORE MANAGEMENT & STATUS UPDATES")
        
        # Ensure we have matches to work with
        if not self.test_matches:
            status_code, response, response_time = self.make_request("GET", "/matches")
            self.test_matches = response if isinstance(response, list) and response else []
        
        if self.test_matches:
            match = self.test_matches[0]
            match_id = match.get("id")
            
            # Test 6.1: Update match score
            score_data = {"scoreA": 21, "scoreB": 19}
            status_code, response, response_time = self.make_request("PUT", f"/matches/{match_id}/score", score_data)
            success = status_code == 200
            self.log_test("Update Match Score", success,
                         f"Score: {score_data['scoreA']}-{score_data['scoreB']}, Status: {status_code}", response_time)
            
            # Test 6.2: Verify match status change
            status_code, response, response_time = self.make_request("GET", "/matches")
            updated_matches = response if isinstance(response, list) else []
            updated_match = next((m for m in updated_matches if m.get("id") == match_id), None)
            
            if updated_match:
                success = updated_match.get("status") == "saved" and updated_match.get("scoreA") == 21
                self.log_test("Match Status Update", success,
                             f"Status: {updated_match.get('status')}, Score: {updated_match.get('scoreA')}-{updated_match.get('scoreB')}", response_time)
            
            # Test 6.3: Verify DUPR rating updates
            status_code, response, response_time = self.make_request("GET", "/players")
            updated_players = response if isinstance(response, list) else []
            
            # Check if any player ratings have changed from default 3.0
            rating_changes = [p for p in updated_players if p.get("rating", 3.0) != 3.0]
            success = len(rating_changes) > 0
            self.log_test("DUPR Rating Updates", success,
                         f"Players with rating changes: {len(rating_changes)}", response_time)
            
            # Test 6.4: Multiple match scoring
            if len(self.test_matches) > 1:
                second_match = self.test_matches[1]
                second_match_id = second_match.get("id")
                score_data_2 = {"scoreA": 15, "scoreB": 21}
                
                status_code, response, response_time = self.make_request("PUT", f"/matches/{second_match_id}/score", score_data_2)
                success = status_code == 200
                self.log_test("Multiple Match Scoring", success,
                             f"Second match score: {score_data_2['scoreA']}-{score_data_2['scoreB']}", response_time)

    # ========================================
    # 7. Round Progression System Tests
    # ========================================
    
    def test_round_progression(self):
        """Test round progression and enhanced reshuffling"""
        print("\n🔄 TESTING ROUND PROGRESSION SYSTEM")
        
        # Test 7.1: Next round generation
        status_code, response, response_time = self.make_request("POST", "/session/next-round")
        success = status_code == 200
        self.log_test("Next Round Generation", success,
                     f"Next round response: {response.get('message', 'Success') if isinstance(response, dict) else 'Success'}", response_time)
        
        # Test 7.2: Verify new matches created
        status_code, response, response_time = self.make_request("GET", "/matches")
        all_matches = response if isinstance(response, list) else []
        round_2_matches = [m for m in all_matches if m.get("roundIndex") == 2]
        success = len(round_2_matches) > 0
        self.log_test("Round 2 Matches Created", success,
                     f"Round 2 matches: {len(round_2_matches)}", response_time)
        
        # Test 7.3: Verify team reshuffling
        if round_2_matches and self.test_matches:
            round_1_teams = set()
            for match in self.test_matches:
                if match.get("roundIndex") == 1:
                    team_a = tuple(sorted(match.get("teamA", [])))
                    team_b = tuple(sorted(match.get("teamB", [])))
                    round_1_teams.add((team_a, team_b))
            
            round_2_teams = set()
            for match in round_2_matches:
                team_a = tuple(sorted(match.get("teamA", [])))
                team_b = tuple(sorted(match.get("teamB", [])))
                round_2_teams.add((team_a, team_b))
            
            # Check for different team combinations
            different_teams = len(round_1_teams.intersection(round_2_teams)) < len(round_1_teams)
            success = different_teams
            self.log_test("Team Reshuffling Verification", success,
                         f"Round 1 teams: {len(round_1_teams)}, Round 2 teams: {len(round_2_teams)}, Different: {different_teams}", response_time)
        
        # Test 7.4: Multiple round progression (Round 2 -> 3)
        status_code, response, response_time = self.make_request("POST", "/session/next-round")
        success = status_code == 200
        self.log_test("Round 3 Generation", success,
                     f"Round 3 response: {response.get('message', 'Success') if isinstance(response, dict) else 'Success'}", response_time)
        
        # Test 7.5: Verify session round tracking
        status_code, response, response_time = self.make_request("GET", "/session")
        success = status_code == 200 and response.get("currentRound", 0) >= 3
        current_round = response.get("currentRound", 0) if isinstance(response, dict) else 0
        self.log_test("Session Round Tracking", success,
                     f"Current round: {current_round}", response_time)

    # ========================================
    # 8. Enhanced Features Validation Tests
    # ========================================
    
    def test_enhanced_features(self):
        """Test enhanced features like reshuffling algorithms and optimization"""
        print("\n🚀 TESTING ENHANCED FEATURES VALIDATION")
        
        # Test 8.1: Enhanced player reshuffling algorithms
        # Get session histories to check partner/opponent tracking
        status_code, response, response_time = self.make_request("GET", "/session")
        success = status_code == 200 and "histories" in response
        histories = response.get("histories", {}) if isinstance(response, dict) else {}
        partner_history = histories.get("partnerHistory", {})
        opponent_history = histories.get("opponentHistory", {})
        
        partner_entries = sum(len(partners) for partners in partner_history.values())
        opponent_entries = sum(len(opponents) for opponents in opponent_history.values())
        
        self.log_test("Enhanced History Tracking", success and (partner_entries > 0 or opponent_entries > 0),
                     f"Partner entries: {partner_entries}, Opponent entries: {opponent_entries}", response_time)
        
        # Test 8.2: Rating balance optimization
        status_code, response, response_time = self.make_request("GET", "/matches")
        current_matches = response if isinstance(response, list) else []
        
        if current_matches and self.test_players:
            # Calculate rating balance across matches
            rating_differences = []
            for match in current_matches:
                team_a_ids = match.get("teamA", [])
                team_b_ids = match.get("teamB", [])
                
                team_a_ratings = [p.get("rating", 3.0) for p in self.test_players if p.get("id") in team_a_ids]
                team_b_ratings = [p.get("rating", 3.0) for p in self.test_players if p.get("id") in team_b_ids]
                
                if team_a_ratings and team_b_ratings:
                    avg_a = sum(team_a_ratings) / len(team_a_ratings)
                    avg_b = sum(team_b_ratings) / len(team_b_ratings)
                    rating_differences.append(abs(avg_a - avg_b))
            
            avg_rating_diff = sum(rating_differences) / len(rating_differences) if rating_differences else 0
            success = avg_rating_diff < 1.0  # Good balance if average difference < 1.0
            self.log_test("Rating Balance Optimization", success,
                         f"Average rating difference: {avg_rating_diff:.2f}", response_time)
        
        # Test 8.3: Court maximization logic
        court_config = {"maximizeCourtUsage": True, "numCourts": 6}
        status_code, response, response_time = self.make_request("PUT", "/session/config", court_config)
        
        # Generate matches with optimization
        status_code, response, response_time = self.make_request("POST", "/session/generate-matches")
        
        # Check court utilization
        status_code, response, response_time = self.make_request("GET", "/matches")
        optimized_matches = response if isinstance(response, list) else []
        courts_used = len(set(m.get("courtIndex", -1) for m in optimized_matches if m.get("courtIndex", -1) >= 0))
        
        success = courts_used > 0
        self.log_test("Court Maximization Logic", success,
                     f"Courts utilized: {courts_used}/6 with optimization enabled", response_time)

    # ========================================
    # 9. Error Handling & Edge Cases Tests
    # ========================================
    
    def test_error_handling(self):
        """Test error handling and edge cases"""
        print("\n⚠️ TESTING ERROR HANDLING & EDGE CASES")
        
        # Test 9.1: Invalid player ID
        fake_id = str(uuid.uuid4())
        status_code, response, response_time = self.make_request("GET", f"/players/{fake_id}")
        success = status_code == 404
        self.log_test("Invalid Player ID Handling", success,
                     f"Status: {status_code} for non-existent player", response_time)
        
        # Test 9.2: Invalid match score update
        fake_match_id = str(uuid.uuid4())
        status_code, response, response_time = self.make_request("PUT", f"/matches/{fake_match_id}/score", {"scoreA": 21, "scoreB": 19})
        success = status_code in [404, 400]  # Should return error
        self.log_test("Invalid Match Score Update", success,
                     f"Status: {status_code} for non-existent match", response_time)
        
        # Test 9.3: Invalid configuration values
        invalid_config = {"numCourts": -1, "playSeconds": 0}
        status_code, response, response_time = self.make_request("PUT", "/session/config", invalid_config)
        success = status_code in [400, 422]  # Should reject invalid values
        self.log_test("Invalid Configuration Rejection", success,
                     f"Status: {status_code} for invalid config", response_time)
        
        # Test 9.4: Session operations without proper setup
        # Try to start session without matches
        status_code, response, response_time = self.make_request("POST", "/session/reset")
        status_code, response, response_time = self.make_request("POST", "/session/start")
        success = status_code in [200, 400]  # Should handle gracefully
        self.log_test("Session Start Without Matches", success,
                     f"Status: {status_code} when starting without matches", response_time)

    # ========================================
    # 10. Performance & Load Testing
    # ========================================
    
    def test_performance(self):
        """Test performance and response times"""
        print("\n⚡ TESTING PERFORMANCE & LOAD")
        
        # Test 10.1: Response time benchmarks
        endpoints_to_test = [
            ("GET", "/session"),
            ("GET", "/players"),
            ("GET", "/categories"),
            ("GET", "/matches")
        ]
        
        total_response_time = 0
        successful_requests = 0
        
        for method, endpoint in endpoints_to_test:
            status_code, response, response_time = self.make_request(method, endpoint)
            success = status_code == 200 and response_time < 2.0  # Under 2 seconds
            
            if success:
                total_response_time += response_time
                successful_requests += 1
                
            self.log_test(f"Response Time - {endpoint}", success,
                         f"Time: {response_time:.3f}s", response_time)
        
        # Test 10.2: Average response time
        avg_response_time = total_response_time / successful_requests if successful_requests > 0 else 0
        success = avg_response_time < 1.0  # Average under 1 second
        self.log_test("Average Response Time", success,
                     f"Average: {avg_response_time:.3f}s across {successful_requests} requests", avg_response_time)
        
        # Test 10.3: Concurrent request handling (simplified)
        import threading
        import queue
        
        def make_concurrent_request(result_queue):
            status_code, response, response_time = self.make_request("GET", "/session")
            result_queue.put((status_code == 200, response_time))
        
        result_queue = queue.Queue()
        threads = []
        
        # Create 5 concurrent requests
        for _ in range(5):
            thread = threading.Thread(target=make_concurrent_request, args=(result_queue,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Collect results
        concurrent_results = []
        while not result_queue.empty():
            concurrent_results.append(result_queue.get())
        
        successful_concurrent = sum(1 for success, _ in concurrent_results if success)
        avg_concurrent_time = sum(time for _, time in concurrent_results) / len(concurrent_results) if concurrent_results else 0
        
        success = successful_concurrent >= 4  # At least 4/5 should succeed
        self.log_test("Concurrent Request Handling", success,
                     f"Successful: {successful_concurrent}/5, Avg time: {avg_concurrent_time:.3f}s", avg_concurrent_time)

    # ========================================
    # Test Execution and Reporting
    # ========================================
    
    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 STARTING COMPREHENSIVE COURTCHIME PRE-DEPLOYMENT TESTING")
        print("=" * 80)
        
        start_time = time.time()
        
        try:
            # Run all test suites
            self.test_database_initialization()
            self.test_player_management()
            self.test_session_management()
            self.test_match_generation()
            self.test_session_flow()
            self.test_score_management()
            self.test_round_progression()
            self.test_enhanced_features()
            self.test_error_handling()
            self.test_performance()
            
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR DURING TESTING: {str(e)}")
            self.log_test("Test Suite Execution", False, f"Critical error: {str(e)}")
        
        total_time = time.time() - start_time
        self.generate_final_report(total_time)
    
    def generate_final_report(self, total_time: float):
        """Generate comprehensive test report"""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE PRE-DEPLOYMENT TEST RESULTS")
        print("=" * 80)
        
        # Calculate statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📈 OVERALL STATISTICS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests} ✅")
        print(f"   Failed: {failed_tests} ❌")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Total Execution Time: {total_time:.2f}s")
        
        # Deployment readiness assessment
        print(f"\n🎯 DEPLOYMENT READINESS ASSESSMENT:")
        
        critical_systems = [
            "Database Initialization",
            "Retrieve All Players", 
            "Generate Matches",
            "Start Session (Play Phase)",
            "Update Match Score",
            "Next Round Generation"
        ]
        
        critical_failures = [result for result in self.test_results 
                           if not result["success"] and any(critical in result["test"] for critical in critical_systems)]
        
        if not critical_failures and success_rate >= 85:
            print("   ✅ READY FOR DEPLOYMENT")
            print("   All critical systems operational, success rate acceptable")
        elif success_rate >= 70:
            print("   ⚠️ DEPLOYMENT WITH CAUTION")
            print("   Some non-critical issues found, monitor closely")
        else:
            print("   ❌ NOT READY FOR DEPLOYMENT")
            print("   Critical issues found, requires fixes before deployment")
        
        # Failed tests summary
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS SUMMARY:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['details']}")
        
        # Success criteria verification
        print(f"\n✅ SUCCESS CRITERIA VERIFICATION:")
        criteria_checks = [
            ("API Endpoints Responding", passed_tests > 0),
            ("Database Operations Working", any("Database" in r["test"] and r["success"] for r in self.test_results)),
            ("Session Management Functional", any("Session" in r["test"] and r["success"] for r in self.test_results)),
            ("Match Generation Working", any("Match" in r["test"] and r["success"] for r in self.test_results)),
            ("Score Management Working", any("Score" in r["test"] and r["success"] for r in self.test_results)),
            ("Round Progression Working", any("Round" in r["test"] and r["success"] for r in self.test_results)),
            ("Enhanced Features Operational", any("Enhanced" in r["test"] and r["success"] for r in self.test_results)),
            ("Error Handling Implemented", any("Error" in r["test"] and r["success"] for r in self.test_results)),
            ("Performance Acceptable", any("Performance" in r["test"] and r["success"] for r in self.test_results))
        ]
        
        for criteria, met in criteria_checks:
            status = "✅" if met else "❌"
            print(f"   {status} {criteria}")
        
        print("\n" + "=" * 80)
        print("🏁 COMPREHENSIVE PRE-DEPLOYMENT TESTING COMPLETE")
        print("=" * 80)

def main():
    """Main execution function"""
    print("CourtChime Comprehensive Pre-Deployment Testing Suite")
    print("====================================================")
    
    # Initialize and run tests
    test_suite = CourtChimeTestSuite()
    test_suite.run_all_tests()

if __name__ == "__main__":
    main()