#!/usr/bin/env python3
"""
Backend API Testing Script for Match Status Update Issue Debugging
Testing the exact API responses step by step as requested
"""

import requests
import json
import time
from typing import Dict, List, Any

# Backend URL from frontend .env
BACKEND_URL = "https://court-timer.preview.emergentagent.com/api"

class MatchStatusDebugger:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
    def log_response(self, step: str, method: str, url: str, response: requests.Response, data: Dict = None):
        """Log detailed API response information"""
        print(f"\n{'='*60}")
        print(f"STEP {step}: {method} {url}")
        if data:
            print(f"REQUEST DATA: {json.dumps(data, indent=2)}")
        print(f"STATUS CODE: {response.status_code}")
        print(f"RESPONSE HEADERS: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"RESPONSE BODY: {json.dumps(response_json, indent=2)}")
            return response_json
        except:
            print(f"RESPONSE TEXT: {response.text}")
            return None
    
    def step1_check_current_matches(self):
        """Step 1: Check Current Match Status"""
        print(f"\n🔍 STEP 1: CHECKING CURRENT MATCH STATUS")
        
        url = f"{BACKEND_URL}/matches"
        response = self.session.get(url)
        matches = self.log_response("1", "GET", url, response)
        
        if matches:
            print(f"\n📊 MATCH ANALYSIS:")
            print(f"Total matches found: {len(matches)}")
            
            for i, match in enumerate(matches):
                print(f"\nMatch {i+1}:")
                print(f"  ID: {match.get('id')}")
                print(f"  Status: {match.get('status')}")
                print(f"  Round: {match.get('roundIndex')}")
                print(f"  Court: {match.get('courtIndex')}")
                print(f"  Category: {match.get('category')}")
                print(f"  ScoreA: {match.get('scoreA')}")
                print(f"  ScoreB: {match.get('scoreB')}")
                print(f"  TeamA: {match.get('teamA')}")
                print(f"  TeamB: {match.get('teamB')}")
        
        return matches
    
    def step2_test_score_saving(self, match_id: str, scoreA: int = 11, scoreB: int = 7):
        """Step 2: Test Score Saving API Response"""
        print(f"\n🎯 STEP 2: TESTING SCORE SAVING API")
        
        url = f"{BACKEND_URL}/matches/{match_id}/score"
        data = {"scoreA": scoreA, "scoreB": scoreB}
        
        response = self.session.put(url, json=data)
        result = self.log_response("2", "PUT", url, response, data)
        
        print(f"\n🔍 CRITICAL ANALYSIS:")
        if result:
            print(f"✅ Response received successfully")
            print(f"📋 Status field in response: {result.get('status', 'NOT FOUND')}")
            print(f"📋 ScoreA in response: {result.get('scoreA', 'NOT FOUND')}")
            print(f"📋 ScoreB in response: {result.get('scoreB', 'NOT FOUND')}")
            
            # Check if status shows "saved"
            if result.get('status') == 'saved':
                print(f"✅ Status correctly shows 'saved'")
            else:
                print(f"❌ Status does NOT show 'saved', shows: {result.get('status')}")
        else:
            print(f"❌ No valid JSON response received")
        
        return result
    
    def step3_verify_database_update(self, match_id: str):
        """Step 3: Verify Database Update"""
        print(f"\n🔄 STEP 3: VERIFYING DATABASE UPDATE")
        
        url = f"{BACKEND_URL}/matches"
        response = self.session.get(url)
        matches = self.log_response("3", "GET", url, response)
        
        if matches:
            # Find the specific match we updated
            updated_match = None
            for match in matches:
                if match.get('id') == match_id:
                    updated_match = match
                    break
            
            if updated_match:
                print(f"\n🎯 UPDATED MATCH ANALYSIS:")
                print(f"  Match ID: {updated_match.get('id')}")
                print(f"  Status: {updated_match.get('status')}")
                print(f"  ScoreA: {updated_match.get('scoreA')}")
                print(f"  ScoreB: {updated_match.get('scoreB')}")
                
                # Verify status change
                if updated_match.get('status') == 'saved':
                    print(f"✅ Database shows status as 'saved'")
                else:
                    print(f"❌ Database status is NOT 'saved', shows: {updated_match.get('status')}")
                
                return updated_match
            else:
                print(f"❌ Match with ID {match_id} not found in database")
        
        return None
    
    def step4_multiple_score_tests(self, matches: List[Dict]):
        """Step 4: Multiple Score Tests"""
        print(f"\n🔄 STEP 4: TESTING MULTIPLE MATCHES")
        
        test_scenarios = [
            {"scoreA": 11, "scoreB": 7},
            {"scoreA": 15, "scoreB": 13},
            {"scoreA": 8, "scoreB": 11}
        ]
        
        results = []
        
        for i, match in enumerate(matches[:3]):  # Test first 3 matches
            if i >= len(test_scenarios):
                break
                
            match_id = match.get('id')
            scenario = test_scenarios[i]
            
            print(f"\n--- Testing Match {i+1} (ID: {match_id}) ---")
            
            # Save score
            put_result = self.step2_test_score_saving(match_id, scenario['scoreA'], scenario['scoreB'])
            
            # Small delay to ensure database update
            time.sleep(1)
            
            # Verify update
            get_result = self.step3_verify_database_update(match_id)
            
            results.append({
                'match_id': match_id,
                'scenario': scenario,
                'put_response': put_result,
                'get_response': get_result,
                'consistent': (put_result and get_result and 
                             put_result.get('status') == get_result.get('status'))
            })
        
        return results
    
    def analyze_consistency(self, results: List[Dict]):
        """Analyze API response consistency"""
        print(f"\n📊 CONSISTENCY ANALYSIS:")
        
        for i, result in enumerate(results):
            print(f"\nMatch {i+1} ({result['match_id'][:8]}...):")
            print(f"  Scenario: {result['scenario']}")
            
            put_status = result['put_response'].get('status') if result['put_response'] else 'NO_RESPONSE'
            get_status = result['get_response'].get('status') if result['get_response'] else 'NO_RESPONSE'
            
            print(f"  PUT response status: {put_status}")
            print(f"  GET response status: {get_status}")
            print(f"  Consistent: {'✅ YES' if result['consistent'] else '❌ NO'}")
            
            if not result['consistent']:
                print(f"  ⚠️  INCONSISTENCY DETECTED!")
    
    def setup_test_environment(self):
        """Setup test environment with test data"""
        print(f"\n🔧 SETTING UP TEST ENVIRONMENT")
        
        # Add test data
        url = f"{BACKEND_URL}/add-test-data"
        response = self.session.post(url)
        self.log_response("SETUP-1", "POST", url, response)
        
        # Generate matches
        url = f"{BACKEND_URL}/session/generate-matches"
        response = self.session.post(url)
        self.log_response("SETUP-2", "POST", url, response)
        
        print(f"✅ Test environment setup complete")
    
    def run_complete_debug_sequence(self):
        """Run the complete debugging sequence as requested"""
        print(f"🚀 STARTING MATCH STATUS UPDATE DEBUGGING")
        print(f"Backend URL: {BACKEND_URL}")
        
        try:
            # Setup test environment
            self.setup_test_environment()
            
            # Step 1: Check current matches
            matches = self.step1_check_current_matches()
            
            if not matches:
                print(f"❌ No matches found. Cannot proceed with testing.")
                return
            
            # Step 4: Test multiple scenarios
            results = self.step4_multiple_score_tests(matches)
            
            # Final analysis
            self.analyze_consistency(results)
            
            # Summary
            print(f"\n{'='*60}")
            print(f"🏁 DEBUGGING SUMMARY")
            print(f"{'='*60}")
            
            consistent_count = sum(1 for r in results if r['consistent'])
            total_tests = len(results)
            
            print(f"Total tests performed: {total_tests}")
            print(f"Consistent responses: {consistent_count}")
            print(f"Inconsistent responses: {total_tests - consistent_count}")
            
            if consistent_count == total_tests:
                print(f"✅ ALL TESTS PASSED - No status update issues detected")
            else:
                print(f"❌ ISSUES DETECTED - Status update inconsistencies found")
                print(f"🔍 Check the detailed logs above for specific issues")
            
        except Exception as e:
            print(f"❌ ERROR during debugging: {str(e)}")
            import traceback
            traceback.print_exc()

def main():
    """Main function to run the debugging"""
    debugger = MatchStatusDebugger()
    debugger.run_complete_debug_sequence()

if __name__ == "__main__":
    main()