#!/usr/bin/env python3
"""
Focused Session Management API Test for SQLite Migration
Tests the recently migrated session management endpoints
"""

import requests
import json
import os
from typing import Dict, List, Any

# Get backend URL from environment
BACKEND_URL = "https://court-timer.preview.emergentagent.com/api"

class SessionMigrationTester:
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

    def test_get_session_sqlite(self):
        """Test GET /api/session - should work with SQLite and create default session if needed"""
        print("=== Testing GET /api/session with SQLite ===")
        try:
            response = self.session.get(f"{self.base_url}/session")
            
            if response.status_code == 200:
                session_data = response.json()
                
                # Verify session structure
                required_fields = ["id", "currentRound", "phase", "timeRemaining", "paused", "config", "histories"]
                missing_fields = [field for field in required_fields if field not in session_data]
                
                if missing_fields:
                    self.log_test("GET /api/session - Structure", False, f"Missing fields: {missing_fields}")
                    return False
                
                # Verify config structure (should include new SQLite fields)
                config = session_data.get("config", {})
                expected_config_fields = ["numCourts", "playSeconds", "bufferSeconds", "allowSingles", "allowDoubles", "allowCrossCategory", "maximizeCourtUsage"]
                missing_config_fields = [field for field in expected_config_fields if field not in config]
                
                if missing_config_fields:
                    self.log_test("GET /api/session - Config Structure", False, f"Missing config fields: {missing_config_fields}")
                    return False
                
                # Verify JSON field handling for histories
                histories = session_data.get("histories", {})
                if not isinstance(histories, dict):
                    self.log_test("GET /api/session - JSON Field Handling", False, f"Histories should be dict, got: {type(histories)}")
                    return False
                
                self.log_test("GET /api/session - SQLite Success", True, f"Session retrieved successfully with all required fields. Config: {config}")
                return True
                
            else:
                self.log_test("GET /api/session - SQLite Failure", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("GET /api/session - Exception", False, f"Exception: {str(e)}")
            return False

    def test_put_session_config_sqlite(self):
        """Test PUT /api/session/config - should work with SQLite and update session config"""
        print("=== Testing PUT /api/session/config with SQLite ===")
        
        # Test configuration with all new fields
        test_config = {
            "numCourts": 8,
            "playSeconds": 900,  # 15 minutes
            "bufferSeconds": 45,  # 45 seconds
            "allowSingles": True,
            "allowDoubles": True,
            "allowCrossCategory": True,  # Test new field
            "maximizeCourtUsage": True   # Test new field
        }
        
        try:
            response = self.session.put(f"{self.base_url}/session/config", json=test_config)
            
            if response.status_code == 200:
                session_data = response.json()
                updated_config = session_data.get("config", {})
                
                # Verify all config fields were updated correctly
                config_match = all(updated_config.get(key) == value for key, value in test_config.items())
                
                if config_match:
                    self.log_test("PUT /api/session/config - Update Success", True, f"Config updated successfully: {updated_config}")
                    
                    # Test persistence by getting session again
                    get_response = self.session.get(f"{self.base_url}/session")
                    if get_response.status_code == 200:
                        persisted_session = get_response.json()
                        persisted_config = persisted_session.get("config", {})
                        
                        persistence_match = all(persisted_config.get(key) == value for key, value in test_config.items())
                        
                        if persistence_match:
                            self.log_test("PUT /api/session/config - Persistence", True, "Configuration persisted correctly in SQLite")
                            return True
                        else:
                            self.log_test("PUT /api/session/config - Persistence", False, f"Config not persisted. Expected: {test_config}, Got: {persisted_config}")
                            return False
                    else:
                        self.log_test("PUT /api/session/config - Persistence Check", False, f"Failed to retrieve session for persistence check: {get_response.status_code}")
                        return False
                else:
                    self.log_test("PUT /api/session/config - Update Failed", False, f"Config not updated properly. Expected: {test_config}, Got: {updated_config}")
                    return False
                    
            else:
                self.log_test("PUT /api/session/config - SQLite Failure", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("PUT /api/session/config - Exception", False, f"Exception: {str(e)}")
            return False

    def test_json_field_handling(self):
        """Test JSON field handling for session config and histories"""
        print("=== Testing JSON Field Handling ===")
        
        try:
            # Test complex config update
            complex_config = {
                "numCourts": 6,
                "playSeconds": 720,
                "bufferSeconds": 30,
                "allowSingles": False,
                "allowDoubles": True,
                "allowCrossCategory": False,
                "maximizeCourtUsage": False
            }
            
            response = self.session.put(f"{self.base_url}/session/config", json=complex_config)
            
            if response.status_code == 200:
                session_data = response.json()
                
                # Verify JSON serialization/deserialization
                config = session_data.get("config", {})
                histories = session_data.get("histories", {})
                
                # Check that boolean values are preserved correctly
                boolean_fields = ["allowSingles", "allowDoubles", "allowCrossCategory", "maximizeCourtUsage"]
                boolean_correct = all(isinstance(config.get(field), bool) for field in boolean_fields)
                
                if boolean_correct:
                    self.log_test("JSON Field Handling - Boolean Types", True, "Boolean fields correctly preserved")
                else:
                    self.log_test("JSON Field Handling - Boolean Types", False, f"Boolean fields not preserved correctly: {config}")
                    return False
                
                # Check that histories is a proper dict
                if isinstance(histories, dict):
                    self.log_test("JSON Field Handling - Histories Dict", True, "Histories field correctly handled as dict")
                    return True
                else:
                    self.log_test("JSON Field Handling - Histories Dict", False, f"Histories should be dict, got: {type(histories)}")
                    return False
                    
            else:
                self.log_test("JSON Field Handling - Request Failed", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("JSON Field Handling - Exception", False, f"Exception: {str(e)}")
            return False

    def test_no_mongodb_errors(self):
        """Verify that session APIs no longer fail with MongoDB errors"""
        print("=== Testing No MongoDB Errors ===")
        
        try:
            # Test multiple session operations to ensure no MongoDB references
            operations = [
                ("GET /api/session", lambda: self.session.get(f"{self.base_url}/session")),
                ("PUT /api/session/config", lambda: self.session.put(f"{self.base_url}/session/config", json={
                    "numCourts": 4,
                    "playSeconds": 600,
                    "bufferSeconds": 30,
                    "allowSingles": True,
                    "allowDoubles": True,
                    "allowCrossCategory": False,
                    "maximizeCourtUsage": False
                }))
            ]
            
            mongodb_errors = []
            
            for op_name, operation in operations:
                try:
                    response = operation()
                    
                    if response.status_code >= 500:
                        # Check if error message contains MongoDB references
                        error_text = response.text.lower()
                        mongodb_keywords = ['mongodb', 'mongo', 'db.', 'collection', 'pymongo']
                        
                        for keyword in mongodb_keywords:
                            if keyword in error_text:
                                mongodb_errors.append(f"{op_name}: {keyword} found in error")
                                break
                    
                except Exception as e:
                    error_str = str(e).lower()
                    mongodb_keywords = ['mongodb', 'mongo', 'db.', 'collection', 'pymongo']
                    
                    for keyword in mongodb_keywords:
                        if keyword in error_str:
                            mongodb_errors.append(f"{op_name}: {keyword} found in exception")
                            break
            
            if not mongodb_errors:
                self.log_test("No MongoDB Errors", True, "No MongoDB references found in session API responses")
                return True
            else:
                self.log_test("No MongoDB Errors", False, f"MongoDB references found: {mongodb_errors}")
                return False
                
        except Exception as e:
            self.log_test("No MongoDB Errors - Exception", False, f"Exception: {str(e)}")
            return False

    def run_focused_tests(self):
        """Run focused tests for session management SQLite migration"""
        print("🎯 FOCUSED SESSION MANAGEMENT SQLITE MIGRATION TESTS")
        print("=" * 60)
        
        # Test 1: GET /api/session
        test1_success = self.test_get_session_sqlite()
        
        # Test 2: PUT /api/session/config  
        test2_success = self.test_put_session_config_sqlite()
        
        # Test 3: JSON field handling
        test3_success = self.test_json_field_handling()
        
        # Test 4: No MongoDB errors
        test4_success = self.test_no_mongodb_errors()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 FOCUSED TEST SUMMARY")
        print("=" * 60)
        
        passed_tests = sum([test1_success, test2_success, test3_success, test4_success])
        total_tests = 4
        
        for result in self.test_results:
            print(f"{result['status']}: {result['test']}")
        
        print(f"\n🎯 FOCUSED TESTS PASSED: {passed_tests}/{total_tests}")
        
        if passed_tests == total_tests:
            print("✅ SESSION MANAGEMENT SQLITE MIGRATION SUCCESSFUL!")
            return True
        else:
            print("❌ SESSION MANAGEMENT SQLITE MIGRATION HAS ISSUES!")
            return False

def main():
    """Main test execution"""
    tester = SessionMigrationTester()
    success = tester.run_focused_tests()
    
    if success:
        print("\n🎉 All session management APIs successfully migrated to SQLite!")
    else:
        print("\n⚠️  Session management migration needs attention!")
    
    return success

if __name__ == "__main__":
    main()