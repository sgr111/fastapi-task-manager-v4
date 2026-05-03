import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Login first
        r = await client.post("/api/v1/auth/login", json={
            "username": "ratetest_1777708596",
            "password": "SecurePass123!"
        })
        
        if r.status_code != 200:
            print(f"Login failed: {r.json()}")
            return
        
        token = r.json()["access_token"]
        
        # Try ONE task creation
        r = await client.post(
            "/api/v1/tasks/",
            json={"title": "Test Task"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        print(f"Status: {r.status_code}")
        print(f"Response: {r.json()}")

asyncio.run(test())