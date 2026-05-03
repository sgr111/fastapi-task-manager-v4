"""
Manual Rate Limiting Verification Script
=========================================

This script manually tests rate limiting without pytest isolation.
It creates a continuous session and verifies slowapi is working correctly.

Usage:
    python verify_rate_limiting.py

Requirements:
    - FastAPI server running: uvicorn app.main:app --reload
    - httpx and asyncio (already in project dependencies)

What it tests:
    ✅ User registration
    ✅ User login & token generation
    ✅ Task creation (30 requests)
    ✅ Rate limiting enforcement at request #31
    ✅ Rate limit headers (RateLimit-Limit, RateLimit-Remaining)
"""

import httpx
import asyncio
import json
from datetime import datetime


class RateLimitVerifier:
    """Verify rate limiting works correctly in continuous session."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = None
        self.token = None
        self.username = f"ratetest_{int(datetime.now().timestamp())}"
        self.email = f"{self.username}@example.com"
        self.password = "RateTestPass123"
    
    async def setup(self):
        """Create async HTTP client."""
        self.client = httpx.AsyncClient(base_url=self.base_url)
    
    async def teardown(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
    
    async def register_user(self) -> bool:
        """Register a test user."""
        print("\n" + "="*70)
        print("1️⃣  REGISTERING USER")
        print("="*70)
        
        try:
            response = await self.client.post(
                "/api/v1/auth/register",
                json={
                    "username": self.username,
                    "email": self.email,
                    "password": self.password
                }
            )
            
            print(f"Username: {self.username}")
            print(f"Email: {self.email}")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 201:
                print("✅ User registered successfully")
                return True
            else:
                print(f"❌ Registration failed: {response.json()}")
                return False
        except Exception as e:
            print(f"❌ Error during registration: {e}")
            return False
    
    async def login_user(self) -> bool:
        """Login user and get JWT token."""
        print("\n" + "="*70)
        print("2️⃣  LOGGING IN & GETTING TOKEN")
        print("="*70)
        
        try:
            response = await self.client.post(
                "/api/v1/auth/login",
                json={
                    "username": self.username,
                    "password": self.password
                }
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                print(f"Token (first 50 chars): {self.token[:50]}...")
                print("✅ Login successful")
                return True
            else:
                print(f"❌ Login failed: {response.json()}")
                return False
        except Exception as e:
            print(f"❌ Error during login: {e}")
            return False
    
    async def test_rate_limiting(self, num_requests: int = 35) -> dict:
        """
        Test rate limiting by making sequential requests.
        
        Args:
            num_requests: Number of requests to make (default 35 to exceed 30/min limit)
        
        Returns:
            Dictionary with test results
        """
        print("\n" + "="*70)
        print(f"3️⃣  TESTING RATE LIMITING ({num_requests} requests)")
        print("="*70)
        print(f"Limit: 30 requests/minute")
        print(f"Making {num_requests} sequential requests to /api/v1/tasks/")
        print("-"*70)
        
        headers = {"Authorization": f"Bearer {self.token}"}
        results = {
            "total_requests": num_requests,
            "successful_requests": 0,
            "rate_limited_requests": 0,
            "error_requests": 0,
            "rate_limit_hit_at": None,
            "rate_limit_headers": None,
            "requests": []
        }
        
        for i in range(1, num_requests + 1):
            try:
                response = await self.client.post(
                    "/api/v1/tasks/",
                    json={"title": f"Rate Limit Test Task {i}"},
                    headers=headers
                )
                
                status = response.status_code
                request_data = {
                    "request_num": i,
                    "status": status,
                    "headers": dict(response.headers)
                }
                results["requests"].append(request_data)
                
                # Format status with emoji
                if status == 201:
                    emoji = "✅"
                    results["successful_requests"] += 1
                elif status == 429:
                    emoji = "❌"
                    results["rate_limited_requests"] += 1
                    if not results["rate_limit_hit_at"]:
                        results["rate_limit_hit_at"] = i
                        # Store rate limit headers for inspection
                        results["rate_limit_headers"] = {
                            "RateLimit-Limit": response.headers.get("RateLimit-Limit", "Not set"),
                            "RateLimit-Remaining": response.headers.get("RateLimit-Remaining", "Not set"),
                            "RateLimit-Reset": response.headers.get("RateLimit-Reset", "Not set"),
                            "Retry-After": response.headers.get("Retry-After", "Not set"),
                        }
                else:
                    emoji = "⚠️"
                    results["error_requests"] += 1
                
                print(f"Request {i:2d}: {status} {emoji}")
                
                # Stop after hitting rate limit for a few requests to confirm it persists
                if status == 429 and results["rate_limited_requests"] >= 3:
                    print(f"\n✅ Rate limiting confirmed! (hit limit at request #{results['rate_limit_hit_at']})")
                    print(f"   Verified persistence: Next 2 requests also returned 429")
                    break
                    
            except Exception as e:
                print(f"Request {i:2d}: ERROR ⚠️ ({str(e)[:50]})")
                results["error_requests"] += 1
        
        return results
    
    def print_summary(self, results: dict):
        """Print test results summary."""
        print("\n" + "="*70)
        print("📊 RATE LIMITING TEST RESULTS")
        print("="*70)
        
        print(f"\nTotal Requests Made: {len(results['requests'])}")
        print(f"Successful (201): {results['successful_requests']} ✅")
        print(f"Rate Limited (429): {results['rate_limited_requests']} ❌")
        print(f"Errors: {results['error_requests']} ⚠️")
        
        if results["rate_limit_hit_at"]:
            print(f"\n🎯 Rate Limit Hit At: Request #{results['rate_limit_hit_at']}")
            print(f"   Expected: Request #31 (30/minute limit)")
            print(f"   Result: {'✅ CORRECT' if results['rate_limit_hit_at'] == 31 else '⚠️ Different'}")
        else:
            print(f"\n⚠️ Rate limit was NOT hit during testing")
            print(f"   Expected: Hit at request #31")
        
        if results["rate_limit_headers"]:
            print(f"\n📋 Rate Limit Headers (when hit):")
            for header, value in results["rate_limit_headers"].items():
                print(f"   {header}: {value}")
        
        print(f"\n{'='*70}")
        if results["rate_limit_hit_at"] == 31 and results["rate_limited_requests"] >= 2:
            print("✅ RATE LIMITING WORKING CORRECTLY!")
            print("="*70)
            return True
        else:
            print("⚠️ RATE LIMITING TEST INCONCLUSIVE")
            print("="*70)
            return False
    
    async def run(self):
        """Run complete rate limiting verification."""
        print("\n")
        print("╔" + "="*68 + "╗")
        print("║" + " "*68 + "║")
        print("║" + "  Manual Rate Limiting Verification".center(68) + "║")
        print("║" + "  FastAPI Task Manager v3".center(68) + "║")
        print("║" + " "*68 + "║")
        print("╚" + "="*68 + "╝")
        
        try:
            # Setup
            await self.setup()
            
            # Register user
            if not await self.register_user():
                print("\n❌ Cannot proceed without registration")
                return
            
            # Login
            if not await self.login_user():
                print("\n❌ Cannot proceed without authentication")
                return
            
            # Test rate limiting
            results = await self.test_rate_limiting(num_requests=35)
            
            # Print summary
            success = self.print_summary(results)
            
            # Print next steps
            print("\n📝 NEXT STEPS:")
            print("-"*70)
            if success:
                print("✅ Rate limiting is working correctly!")
                print("   - You can safely skip rate limit tests in pytest")
                print("   - Use: pytest -v")
            else:
                print("⚠️  Rate limiting behavior was unexpected")
                print("   - Check if slowapi is properly configured")
                print("   - Verify @limiter.limit() decorators on endpoints")
            
            print("\n💾 Test Data Created:")
            print(f"   Username: {self.username}")
            print(f"   Email: {self.email}")
            print("   (You can delete this user from database if needed)")
            
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            print("\n📋 Troubleshooting:")
            print("   1. Is FastAPI server running?")
            print("      uvicorn app.main:app --reload")
            print("   2. Is it on http://localhost:8000?")
            print("   3. Are all dependencies installed?")
            print("      pip install -r requirements.txt")
        
        finally:
            # Cleanup
            await self.teardown()


async def main():
    """Run the verification script."""
    verifier = RateLimitVerifier()
    await verifier.run()


if __name__ == "__main__":
    asyncio.run(main())
