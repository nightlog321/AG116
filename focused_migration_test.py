#!/usr/bin/env python3
"""
Focused SQLite Migration Test - Testing only the migrated APIs
"""

import requests
import json

# Get backend URL from environment
BACKEND_URL = "https://court-timer.preview.emergentagent.com/api"

class FocusedMigrationTester:
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

    def test_sqlite_migrated_apis(self):
        """Test only the APIs that have been migrated to SQLite"""
        print("=== Testing SQLite Migrated APIs ===")
        
        # 1. Clear all data and reinitialize
        print("--- Data Management (SQLite) ---")
        try:
            response = self.session.delete(f"{self.base_url}/clear-all-data")
            if response.status_code == 200:
                self.log_test("DELETE /api/clear-all-data", True, f"Response: {response.json()}")
            else:
                self.log_test("DELETE /api/clear-all-data", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("DELETE /api/clear-all-data", False, f"Exception: {str(e)}")

        # 2. Add test data
        try:
            response = self.session.post(f"{self.base_url}/add-test-data")
            if response.status_code == 200:
                data = response.json()
                self.log_test("POST /api/add-test-data", True, f"Response: {data}")
            else:
                self.log_test("POST /api/add-test-data", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("POST /api/add-test-data", False, f"Exception: {str(e)}")

        # 3. Test Categories APIs (SQLite)
        print("--- Categories APIs (SQLite) ---")
        try:
            response = self.session.get(f"{self.base_url}/categories")
            if response.status_code == 200:
                categories = response.json()
                expected_categories = ["Beginner", "Intermediate", "Advanced"]
                category_names = [cat["name"] for cat in categories]
                
                if all(cat in category_names for cat in expected_categories):
                    self.log_test("GET /api/categories", True, f"Found categories: {category_names}")
                else:
                    self.log_test("GET /api/categories", False, f"Missing categories. Found: {category_names}")
            else:
                self.log_test("GET /api/categories", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/categories", False, f"Exception: {str(e)}")

        # 4. Create and delete a category
        try:
            new_category = {"name": "Test Category", "description": "Test description"}
            response = self.session.post(f"{self.base_url}/categories", json=new_category)
            if response.status_code == 200:
                category = response.json()
                self.log_test("POST /api/categories", True, f"Created: {category['name']}")
                
                # Delete the category
                category_id = category["id"]
                delete_response = self.session.delete(f"{self.base_url}/categories/{category_id}")
                if delete_response.status_code == 200:
                    self.log_test("DELETE /api/categories/{id}", True, f"Deleted category: {category['name']}")
                else:
                    self.log_test("DELETE /api/categories/{id}", False, f"Status: {delete_response.status_code}")
            else:
                self.log_test("POST /api/categories", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("POST /api/categories", False, f"Exception: {str(e)}")

        # 5. Test Players APIs (SQLite)
        print("--- Players APIs (SQLite) ---")
        try:
            response = self.session.get(f"{self.base_url}/players")
            if response.status_code == 200:
                players = response.json()
                self.log_test("GET /api/players", True, f"Found {len(players)} players with DUPR ratings")
                
                # Verify DUPR fields
                if players:
                    player = players[0]
                    dupr_fields = ["rating", "matchesPlayed", "wins", "losses", "recentForm", "ratingHistory"]
                    missing_fields = [field for field in dupr_fields if field not in player]
                    
                    if not missing_fields:
                        self.log_test("DUPR Fields Check", True, "All DUPR fields present")
                    else:
                        self.log_test("DUPR Fields Check", False, f"Missing DUPR fields: {missing_fields}")
            else:
                self.log_test("GET /api/players", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/players", False, f"Exception: {str(e)}")

        # 6. Create, update, and delete a player
        try:
            new_player = {"name": "Test Player", "category": "Beginner"}
            response = self.session.post(f"{self.base_url}/players", json=new_player)
            if response.status_code == 200:
                player = response.json()
                self.log_test("POST /api/players", True, f"Created: {player['name']} with rating {player['rating']}")
                
                # Update the player
                player_id = player["id"]
                update_data = {"name": "Updated Test Player", "category": "Advanced"}
                update_response = self.session.put(f"{self.base_url}/players/{player_id}", json=update_data)
                if update_response.status_code == 200:
                    updated_player = update_response.json()
                    self.log_test("PUT /api/players/{id}", True, f"Updated: {updated_player['name']} -> {updated_player['category']}")
                else:
                    self.log_test("PUT /api/players/{id}", False, f"Status: {update_response.status_code}")
                
                # Delete the player
                delete_response = self.session.delete(f"{self.base_url}/players/{player_id}")
                if delete_response.status_code == 200:
                    self.log_test("DELETE /api/players/{id}", True, f"Deleted player: {player['name']}")
                else:
                    self.log_test("DELETE /api/players/{id}", False, f"Status: {delete_response.status_code}")
            else:
                self.log_test("POST /api/players", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("POST /api/players", False, f"Exception: {str(e)}")

        # 7. Test Matches APIs (Partially SQLite - GET operations only)
        print("--- Matches APIs (Partially SQLite) ---")
        try:
            response = self.session.get(f"{self.base_url}/matches")
            if response.status_code == 200:
                matches = response.json()
                self.log_test("GET /api/matches", True, f"Retrieved {len(matches)} matches from SQLite")
            else:
                self.log_test("GET /api/matches", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/matches", False, f"Exception: {str(e)}")

        try:
            response = self.session.get(f"{self.base_url}/matches/round/1")
            if response.status_code == 200:
                matches = response.json()
                self.log_test("GET /api/matches/round/1", True, f"Retrieved {len(matches)} matches for round 1")
            else:
                self.log_test("GET /api/matches/round/1", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/matches/round/1", False, f"Exception: {str(e)}")

    def test_mongodb_dependent_apis(self):
        """Test APIs that still depend on MongoDB (expected to fail)"""
        print("=== Testing MongoDB Dependent APIs (Expected to Fail) ===")
        
        # Session APIs still use MongoDB
        try:
            response = self.session.get(f"{self.base_url}/session")
            if response.status_code == 200:
                self.log_test("GET /api/session (MongoDB)", False, "Unexpected success - should fail due to MongoDB dependency")
            else:
                self.log_test("GET /api/session (MongoDB)", True, f"Expected failure: Status {response.status_code} (MongoDB not available)")
        except Exception as e:
            self.log_test("GET /api/session (MongoDB)", True, f"Expected failure: {str(e)}")

        try:
            config = {"numCourts": 6, "playSeconds": 720, "bufferSeconds": 30}
            response = self.session.put(f"{self.base_url}/session/config", json=config)
            if response.status_code == 200:
                self.log_test("PUT /api/session/config (MongoDB)", False, "Unexpected success - should fail due to MongoDB dependency")
            else:
                self.log_test("PUT /api/session/config (MongoDB)", True, f"Expected failure: Status {response.status_code} (MongoDB not available)")
        except Exception as e:
            self.log_test("PUT /api/session/config (MongoDB)", True, f"Expected failure: {str(e)}")

    def run_focused_tests(self):
        """Run focused migration tests"""
        print("🔄 Starting Focused SQLite Migration Tests")
        print(f"Backend URL: {self.base_url}")
        print("=" * 80)
        
        self.test_sqlite_migrated_apis()
        self.test_mongodb_dependent_apis()
        
        # Print summary
        print("=" * 80)
        print("🏁 Focused Migration Test Summary")
        print("=" * 80)
        
        sqlite_tests = [r for r in self.test_results if "SQLite" in r["test"] or "POST /api" in r["test"] or "GET /api" in r["test"] or "DELETE /api" in r["test"] or "PUT /api/players" in r["test"]]
        mongodb_tests = [r for r in self.test_results if "MongoDB" in r["test"]]
        
        sqlite_passed = [r for r in sqlite_tests if r["success"]]
        sqlite_failed = [r for r in sqlite_tests if not r["success"]]
        
        mongodb_passed = [r for r in mongodb_tests if r["success"]]  # These are "expected failures"
        mongodb_failed = [r for r in mongodb_tests if not r["success"]]
        
        print(f"📊 SQLite Migrated APIs:")
        print(f"   ✅ WORKING: {len(sqlite_passed)}")
        print(f"   ❌ BROKEN: {len(sqlite_failed)}")
        
        print(f"📊 MongoDB Dependent APIs:")
        print(f"   ✅ EXPECTED FAILURES: {len(mongodb_passed)}")
        print(f"   ❌ UNEXPECTED: {len(mongodb_failed)}")
        
        if sqlite_failed:
            print(f"\n❌ BROKEN SQLite APIs:")
            for test in sqlite_failed:
                print(f"   • {test['test']}: {test['details']}")
        
        if mongodb_failed:
            print(f"\n⚠️  UNEXPECTED MongoDB Results:")
            for test in mongodb_failed:
                print(f"   • {test['test']}: {test['details']}")
        
        sqlite_success_rate = (len(sqlite_passed) / len(sqlite_tests)) * 100 if sqlite_tests else 0
        print(f"\n📈 SQLite Migration Success Rate: {sqlite_success_rate:.1f}%")
        
        return len(sqlite_failed) == 0

if __name__ == "__main__":
    tester = FocusedMigrationTester()
    success = tester.run_focused_tests()
    
    if success:
        print("\n🎉 All SQLite migrated APIs are working correctly!")
        print("📝 Note: MongoDB-dependent APIs are expected to fail until migration is complete.")
    else:
        print("\n⚠️  Some SQLite migrated APIs are not working. Check the details above.")