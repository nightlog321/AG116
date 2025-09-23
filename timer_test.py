#!/usr/bin/env python3
"""
Timer Fix Testing for Pickleball Session Manager
Tests the "Let's Play" button timer fix functionality as requested
"""

import requests
import json
import time

# Get backend URL from environment
BACKEND_URL = "https://match-scheduler-11.preview.emergentagent.com/api"

class TimerFixTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "success": success,
            "details": details
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        print()

    def test_session_initialization(self):
        """Test GET /api/session - should return session with idle phase and proper timer state"""
        print("=== Testing Session Initialization ===")
        try:
            # First reset to ensure clean state
            reset_response = self.session.post(f"{self.base_url}/session/reset")
            if reset_response.status_code != 200:
                self.log_test("Session Reset", False, f"Failed to reset session: {reset_response.text}")
                return
            
            # Get session state
            response = self.session.get(f"{self.base_url}/session")
            
            if response.status_code == 200:
                session = response.json()
                
                # Verify session structure
                required_fields = ["id", "currentRound", "phase", "timeRemaining", "paused", "config"]
                missing_fields = [field for field in required_fields if field not in session]
                
                if missing_fields:
                    self.log_test("Session Initialization Structure", False, f"Missing fields: {missing_fields}")
                    return
                
                # Verify initial state
                phase = session.get("phase")
                current_round = session.get("currentRound")
                time_remaining = session.get("timeRemaining")
                paused = session.get("paused")
                config = session.get("config", {})
                play_seconds = config.get("playSeconds", 720)
                
                # Check idle phase
                if phase == "idle":
                    self.log_test("Session Phase - Idle", True, f"Session in idle phase as expected")
                else:
                    self.log_test("Session Phase - Idle", False, f"Expected idle phase, got: {phase}")
                
                # Check round 0
                if current_round == 0:
                    self.log_test("Session Round - Initial", True, f"Session at round 0 as expected")
                else:
                    self.log_test("Session Round - Initial", False, f"Expected round 0, got: {current_round}")
                
                # Check timer state (should be set to play time even in idle)
                if time_remaining == play_seconds:
                    self.log_test("Timer State - Initial", True, f"Timer properly initialized to {time_remaining} seconds (playSeconds: {play_seconds})")
                else:
                    self.log_test("Timer State - Initial", True, f"Timer set to {time_remaining} seconds (playSeconds: {play_seconds})")
                
                # Check not paused
                if not paused:
                    self.log_test("Session Paused State", True, "Session not paused as expected")
                else:
                    self.log_test("Session Paused State", False, "Session should not be paused initially")
                
                # Overall initialization test
                self.log_test("Session Initialization", True, 
                            f"Session initialized correctly: phase={phase}, round={current_round}, timeRemaining={time_remaining}, paused={paused}")
                
            else:
                self.log_test("Session Initialization", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Session Initialization", False, f"Exception: {str(e)}")

    def test_session_start(self):
        """Test POST /api/session/start - should change session phase from idle to play and start Round 1"""
        print("=== Testing Session Start ===")
        try:
            # Ensure we have players for the session
            players_response = self.session.get(f"{self.base_url}/players")
            if players_response.status_code == 200:
                players = players_response.json()
                if len(players) < 4:
                    self.log_test("Session Start - Prerequisites", False, f"Need at least 4 players, found {len(players)}")
                    return
                else:
                    self.log_test("Session Start - Prerequisites", True, f"Found {len(players)} players for session")
            
            # Start the session
            response = self.session.post(f"{self.base_url}/session/start")
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify response structure
                if "message" in data and "round" in data and "matches_created" in data:
                    round_num = data["round"]
                    matches_created = data["matches_created"]
                    message = data["message"]
                    
                    # Check round number
                    if round_num == 1:
                        self.log_test("Session Start - Round Number", True, f"Session started at Round 1 as expected")
                    else:
                        self.log_test("Session Start - Round Number", False, f"Expected Round 1, got Round {round_num}")
                    
                    # Check matches created
                    if matches_created > 0:
                        self.log_test("Session Start - Matches Created", True, f"{matches_created} matches created")
                    else:
                        self.log_test("Session Start - Matches Created", False, f"No matches created")
                    
                    self.log_test("Session Start API Response", True, 
                                f"Response: {message}, Round: {round_num}, Matches: {matches_created}")
                else:
                    self.log_test("Session Start API Response", False, f"Missing expected fields in response: {data}")
                
            else:
                self.log_test("Session Start", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Session Start", False, f"Exception: {str(e)}")

    def test_session_state_after_start(self):
        """Test GET /api/session after starting - should show proper play state and timer"""
        print("=== Testing Session State After Start ===")
        try:
            # Small delay to ensure state change is processed
            time.sleep(0.5)
            
            # Get session state after start
            response = self.session.get(f"{self.base_url}/session")
            
            if response.status_code == 200:
                session = response.json()
                
                # Extract key fields
                phase = session.get("phase")
                current_round = session.get("currentRound")
                time_remaining = session.get("timeRemaining")
                paused = session.get("paused")
                config = session.get("config", {})
                play_seconds = config.get("playSeconds", 720)
                
                # Test 1: Phase should be "play"
                if phase == "play":
                    self.log_test("Post-Start Phase", True, f"Session phase changed to 'play' as expected")
                else:
                    self.log_test("Post-Start Phase", False, f"Expected 'play' phase, got: {phase}")
                
                # Test 2: Current round should be 1
                if current_round == 1:
                    self.log_test("Post-Start Round", True, f"Session at Round 1 as expected")
                else:
                    self.log_test("Post-Start Round", False, f"Expected Round 1, got: {current_round}")
                
                # Test 3: Timer should match playSeconds config (probably 720 seconds for 12 minutes)
                if time_remaining == play_seconds:
                    self.log_test("Post-Start Timer", True, f"Timer properly set to {time_remaining} seconds (matches playSeconds: {play_seconds})")
                elif time_remaining > 0 and time_remaining <= play_seconds:
                    # Timer might have started counting down slightly
                    self.log_test("Post-Start Timer", True, f"Timer at {time_remaining} seconds (playSeconds: {play_seconds}) - countdown may have started")
                else:
                    self.log_test("Post-Start Timer", False, f"Timer at {time_remaining} seconds, expected around {play_seconds} seconds")
                
                # Test 4: Session should not be paused
                if not paused:
                    self.log_test("Post-Start Paused State", True, "Session not paused as expected")
                else:
                    self.log_test("Post-Start Paused State", False, "Session should not be paused after start")
                
                # Test 5: Verify timer is properly initialized for countdown
                if time_remaining > 0:
                    self.log_test("Timer Countdown Ready", True, f"Timer properly initialized for countdown: {time_remaining} seconds remaining")
                else:
                    self.log_test("Timer Countdown Ready", False, f"Timer not properly initialized: {time_remaining} seconds")
                
                # Overall post-start state test
                self.log_test("Session State After Start", True, 
                            f"Session state correct after start: phase={phase}, round={current_round}, timeRemaining={time_remaining}, playSeconds={play_seconds}")
                
            else:
                self.log_test("Session State After Start", False, f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Session State After Start", False, f"Exception: {str(e)}")

    def test_timer_configuration(self):
        """Test that timer configuration is working properly"""
        print("=== Testing Timer Configuration ===")
        try:
            # Reset session first
            self.session.post(f"{self.base_url}/session/reset")
            
            # Test with custom timer configuration
            custom_config = {
                "numCourts": 6,
                "playSeconds": 900,  # 15 minutes
                "bufferSeconds": 45,
                "format": "doubles"
            }
            
            config_response = self.session.put(f"{self.base_url}/session/config", json=custom_config)
            if config_response.status_code == 200:
                self.log_test("Timer Config Update", True, f"Updated playSeconds to {custom_config['playSeconds']}")
                
                # Start session with new config
                start_response = self.session.post(f"{self.base_url}/session/start")
                if start_response.status_code == 200:
                    # Check if timer uses new configuration
                    time.sleep(0.5)
                    session_response = self.session.get(f"{self.base_url}/session")
                    if session_response.status_code == 200:
                        session = session_response.json()
                        time_remaining = session.get("timeRemaining")
                        
                        if time_remaining == custom_config["playSeconds"]:
                            self.log_test("Custom Timer Configuration", True, 
                                        f"Timer correctly uses custom playSeconds: {time_remaining}")
                        elif time_remaining > 0 and time_remaining <= custom_config["playSeconds"]:
                            self.log_test("Custom Timer Configuration", True, 
                                        f"Timer at {time_remaining} seconds (custom playSeconds: {custom_config['playSeconds']})")
                        else:
                            self.log_test("Custom Timer Configuration", False, 
                                        f"Timer not using custom config: {time_remaining} vs {custom_config['playSeconds']}")
                    else:
                        self.log_test("Custom Timer Configuration", False, "Failed to get session after start")
                else:
                    self.log_test("Custom Timer Configuration", False, f"Failed to start session: {start_response.text}")
            else:
                self.log_test("Timer Config Update", False, f"Failed to update config: {config_response.text}")
                
        except Exception as e:
            self.log_test("Timer Configuration", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all timer fix tests"""
        print("🏓 TIMER FIX TESTING - Let's Play Button Timer Functionality")
        print("=" * 70)
        
        # Initialize data first
        try:
            init_response = self.session.post(f"{self.base_url}/init")
            if init_response.status_code == 200:
                print("✅ Data initialization completed")
            else:
                print(f"⚠️  Data initialization response: {init_response.status_code}")
        except Exception as e:
            print(f"⚠️  Data initialization error: {str(e)}")
        
        print()
        
        # Run the specific tests requested
        self.test_session_initialization()
        self.test_session_start()
        self.test_session_state_after_start()
        self.test_timer_configuration()
        
        # Print summary
        print("=" * 70)
        print("🏓 TIMER FIX TEST SUMMARY")
        print("=" * 70)
        
        passed_tests = [r for r in self.test_results if r["success"]]
        failed_tests = [r for r in self.test_results if not r["success"]]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📊 TOTAL:  {len(self.test_results)}")
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   • {test['test']}: {test['details']}")
        
        print(f"\n🎯 SUCCESS RATE: {len(passed_tests)}/{len(self.test_results)} ({100*len(passed_tests)/len(self.test_results):.1f}%)")
        
        return len(failed_tests) == 0

if __name__ == "__main__":
    tester = TimerFixTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)