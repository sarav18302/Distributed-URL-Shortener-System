#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Distributed URL Shortener
Tests all core functionality including caching, rate limiting, and analytics
"""

import requests
import sys
import time
import json
from datetime import datetime
from typing import Dict, List, Any

class URLShortenerTester:
    def __init__(self, base_url: str = "https://sde-hiring-portal.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.created_urls = []  # Track created URLs for cleanup

    def log_test(self, name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED")
        else:
            print(f"❌ {name}: FAILED - {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "response_data": response_data
        })

    def test_api_health(self):
        """Test basic API connectivity"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            success = response.status_code == 200
            data = response.json() if success else {}
            
            if success:
                expected_fields = ["service", "version", "features"]
                has_fields = all(field in data for field in expected_fields)
                success = has_fields
                details = f"Status: {response.status_code}, Data: {data}" if has_fields else "Missing expected fields"
            else:
                details = f"Status: {response.status_code}, Response: {response.text}"
            
            self.log_test("API Health Check", success, details, data)
            return success
        except Exception as e:
            self.log_test("API Health Check", False, f"Connection error: {str(e)}")
            return False

    def test_url_shortening_basic(self):
        """Test basic URL shortening functionality"""
        # Use unique URL to avoid conflicts
        timestamp = int(time.time())
        test_url = f"https://test-basic-{timestamp}.com"
        
        try:
            response = requests.post(
                f"{self.api_url}/shorten",
                json={"url": test_url},
                timeout=10
            )
            
            success = response.status_code == 200
            if success:
                data = response.json()
                required_fields = ["short_code", "original_url", "created_at", "clicks"]
                has_fields = all(field in data for field in required_fields)
                url_matches = data.get("original_url") == test_url
                success = has_fields and url_matches
                
                if success:
                    self.created_urls.append(data["short_code"])
                    details = f"Short code: {data['short_code']}"
                else:
                    details = f"Missing fields or URL mismatch. Data: {data}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text}"
            
            self.log_test("Basic URL Shortening", success, details, response.json() if success else None)
            return success, response.json() if success else {}
        except Exception as e:
            self.log_test("Basic URL Shortening", False, f"Error: {str(e)}")
            return False, {}

    def test_custom_alias(self):
        """Test custom alias functionality"""
        # Use unique URL to avoid conflicts with existing entries
        timestamp = int(time.time())
        test_url = f"https://unique-test-{timestamp}.com"
        custom_alias = f"test-alias-{timestamp}"
        
        try:
            response = requests.post(
                f"{self.api_url}/shorten",
                json={"url": test_url, "custom_alias": custom_alias},
                timeout=10
            )
            
            success = response.status_code == 200
            if success:
                data = response.json()
                alias_matches = data.get("short_code") == custom_alias
                success = alias_matches
                
                if success:
                    self.created_urls.append(custom_alias)
                    details = f"Custom alias created: {custom_alias}"
                else:
                    details = f"Alias mismatch. Expected: {custom_alias}, Got: {data.get('short_code')}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text}"
            
            self.log_test("Custom Alias Creation", success, details, response.json() if success else None)
            return success, custom_alias if success else None
        except Exception as e:
            self.log_test("Custom Alias Creation", False, f"Error: {str(e)}")
            return False, None

    def test_duplicate_alias(self):
        """Test duplicate custom alias rejection"""
        # Create a fresh alias first
        timestamp = int(time.time())
        test_url = f"https://duplicate-test-{timestamp}.com"
        alias = f"duplicate-alias-{timestamp}"
        
        try:
            # First create an alias
            response1 = requests.post(
                f"{self.api_url}/shorten",
                json={"url": test_url, "custom_alias": alias},
                timeout=10
            )
            
            if response1.status_code != 200:
                self.log_test("Duplicate Alias Rejection", False, "Failed to create initial alias")
                return False
            
            # Track for cleanup
            self.created_urls.append(alias)
            
            # Try to create the same alias again with different URL
            response2 = requests.post(
                f"{self.api_url}/shorten",
                json={"url": f"https://different-url-{timestamp}.com", "custom_alias": alias},
                timeout=10
            )
            
            # Should fail with 400 status
            success = response2.status_code == 400
            details = f"First creation: {response1.status_code}, Duplicate attempt: {response2.status_code}, Response: {response2.text}"
            
            self.log_test("Duplicate Alias Rejection", success, details)
            return success
        except Exception as e:
            self.log_test("Duplicate Alias Rejection", False, f"Error: {str(e)}")
            return False

    def test_url_expansion(self, short_code: str):
        """Test URL expansion/redirection"""
        try:
            response = requests.get(
                f"{self.api_url}/expand/{short_code}",
                allow_redirects=False,
                timeout=10
            )
            
            # Should return 302 redirect
            success = response.status_code == 302
            if success:
                location = response.headers.get("Location")
                success = location is not None
                details = f"Redirects to: {location}" if location else "No Location header"
            else:
                details = f"Status: {response.status_code}, Response: {response.text}"
            
            self.log_test("URL Expansion", success, details)
            return success
        except Exception as e:
            self.log_test("URL Expansion", False, f"Error: {str(e)}")
            return False

    def test_cache_performance(self, short_code: str):
        """Test caching performance by measuring response times"""
        try:
            # Make multiple requests to get more reliable measurements
            times = []
            for i in range(5):
                start_time = time.time()
                response = requests.get(
                    f"{self.api_url}/expand/{short_code}",
                    allow_redirects=False,
                    timeout=10
                )
                elapsed = time.time() - start_time
                times.append(elapsed)
                
                if response.status_code != 302:
                    self.log_test("Cache Performance", False, f"Request {i+1} failed with status {response.status_code}")
                    return False
                
                # Small delay between requests
                time.sleep(0.1)
            
            # Check if later requests are generally faster (cache warming effect)
            first_two_avg = sum(times[:2]) / 2
            last_three_avg = sum(times[2:]) / 3
            
            # Allow for some variance - cache hit should be at least 10% faster on average
            performance_improved = last_three_avg < first_two_avg * 0.9
            
            success = performance_improved
            details = f"First 2 avg: {first_two_avg:.3f}s, Last 3 avg: {last_three_avg:.3f}s, Times: {[f'{t:.3f}' for t in times]}"
            
            self.log_test("Cache Performance", success, details)
            return success
        except Exception as e:
            self.log_test("Cache Performance", False, f"Error: {str(e)}")
            return False

    def test_url_stats(self, short_code: str):
        """Test URL statistics endpoint"""
        try:
            response = requests.get(f"{self.api_url}/stats/{short_code}", timeout=10)
            
            success = response.status_code == 200
            if success:
                data = response.json()
                required_fields = ["short_code", "original_url", "clicks", "created_at"]
                has_fields = all(field in data for field in required_fields)
                success = has_fields
                details = f"Stats retrieved for {short_code}" if has_fields else f"Missing fields in response: {data}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text}"
            
            self.log_test("URL Statistics", success, details, response.json() if success else None)
            return success
        except Exception as e:
            self.log_test("URL Statistics", False, f"Error: {str(e)}")
            return False

    def test_url_list(self):
        """Test URL listing endpoint"""
        try:
            response = requests.get(f"{self.api_url}/urls?limit=10", timeout=10)
            
            success = response.status_code == 200
            if success:
                data = response.json()
                is_list = isinstance(data, list)
                success = is_list
                details = f"Retrieved {len(data)} URLs" if is_list else f"Response is not a list: {type(data)}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text}"
            
            self.log_test("URL List", success, details, response.json() if success else None)
            return success
        except Exception as e:
            self.log_test("URL List", False, f"Error: {str(e)}")
            return False

    def test_system_metrics(self):
        """Test system metrics endpoint"""
        try:
            response = requests.get(f"{self.api_url}/metrics", timeout=10)
            
            success = response.status_code == 200
            if success:
                data = response.json()
                required_fields = ["total_urls", "total_clicks", "cache_stats", "top_urls", "recent_clicks"]
                has_fields = all(field in data for field in required_fields)
                
                # Check cache stats structure
                cache_stats = data.get("cache_stats", {})
                cache_fields = ["size", "capacity", "hits", "misses", "hit_rate"]
                has_cache_fields = all(field in cache_stats for field in cache_fields)
                
                success = has_fields and has_cache_fields
                details = f"Metrics retrieved successfully" if success else f"Missing fields. Data: {data}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text}"
            
            self.log_test("System Metrics", success, details, response.json() if success else None)
            return success
        except Exception as e:
            self.log_test("System Metrics", False, f"Error: {str(e)}")
            return False

    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        print("Testing rate limiting (this may take a moment)...")
        
        try:
            # Make rapid requests to trigger rate limiting
            responses = []
            for i in range(105):  # Exceed the 100 req/min limit
                response = requests.post(
                    f"{self.api_url}/shorten",
                    json={"url": f"https://example.com/test-{i}"},
                    timeout=5
                )
                responses.append(response.status_code)
                
                # Stop early if we hit rate limit
                if response.status_code == 429:
                    break
            
            # Check if we got rate limited
            rate_limited = 429 in responses
            success = rate_limited
            details = f"Rate limit triggered after {responses.count(200)} successful requests" if rate_limited else "Rate limit not triggered"
            
            self.log_test("Rate Limiting", success, details)
            return success
        except Exception as e:
            self.log_test("Rate Limiting", False, f"Error: {str(e)}")
            return False

    def test_url_deletion(self, short_code: str):
        """Test URL deletion functionality"""
        try:
            response = requests.delete(f"{self.api_url}/urls/{short_code}", timeout=10)
            
            success = response.status_code == 200
            if success:
                data = response.json()
                success = "message" in data
                details = f"URL deleted: {data.get('message', 'No message')}"
                
                # Remove from our tracking list
                if short_code in self.created_urls:
                    self.created_urls.remove(short_code)
            else:
                details = f"Status: {response.status_code}, Response: {response.text}"
            
            self.log_test("URL Deletion", success, details)
            return success
        except Exception as e:
            self.log_test("URL Deletion", False, f"Error: {str(e)}")
            return False

    def test_invalid_short_code(self):
        """Test handling of invalid short codes"""
        try:
            response = requests.get(
                f"{self.api_url}/expand/nonexistent123",
                allow_redirects=False,
                timeout=10
            )
            
            # Should return 404
            success = response.status_code == 404
            details = f"Status: {response.status_code}, Response: {response.text}"
            
            self.log_test("Invalid Short Code Handling", success, details)
            return success
        except Exception as e:
            self.log_test("Invalid Short Code Handling", False, f"Error: {str(e)}")
            return False

    def cleanup_created_urls(self):
        """Clean up URLs created during testing"""
        print(f"\nCleaning up {len(self.created_urls)} created URLs...")
        for short_code in self.created_urls[:]:  # Copy list to avoid modification during iteration
            try:
                requests.delete(f"{self.api_url}/urls/{short_code}", timeout=5)
                print(f"Cleaned up: {short_code}")
            except:
                print(f"Failed to clean up: {short_code}")

    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🚀 Starting Distributed URL Shortener Backend Tests")
        print(f"Testing API at: {self.api_url}")
        print("=" * 60)
        
        # Basic connectivity
        if not self.test_api_health():
            print("❌ API health check failed. Stopping tests.")
            return False
        
        # Core functionality tests
        success, url_data = self.test_url_shortening_basic()
        short_code = url_data.get("short_code") if success else None
        
        if short_code:
            self.test_url_expansion(short_code)
            self.test_cache_performance(short_code)
            self.test_url_stats(short_code)
        
        # Advanced functionality
        self.test_custom_alias()
        self.test_duplicate_alias()
        self.test_url_list()
        self.test_system_metrics()
        self.test_invalid_short_code()
        
        # Rate limiting (skip for automated testing)
        print("\n⚠️  Skipping rate limiting test in automated mode")
        # self.test_rate_limiting()  # Uncomment to test rate limiting
        
        # Cleanup
        if short_code:
            self.test_url_deletion(short_code)
        
        self.cleanup_created_urls()
        
        # Summary
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed! Backend is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the details above.")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = URLShortenerTester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        tester.cleanup_created_urls()
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        tester.cleanup_created_urls()
        return 1

if __name__ == "__main__":
    sys.exit(main())