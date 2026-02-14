"""Load sample vendors and tenders"""

import json
import httpx
import asyncio

API_BASE = "http://localhost:8000/api/v1"


async def load_vendors():
    """Load sample vendors"""
    print("\n Loading Vendors...")
    
    with open("data/sample/vendors.json", "r") as f:
        vendors = json.load(f)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for vendor in vendors:
            try:
                response = await client.post(f"{API_BASE}/vendors/", json=vendor)
                if response.status_code == 201:
                    print(f"Loaded vendor: {vendor['company_name']}")
                else:
                    print(f"Failed: {vendor['company_name']} - {response.text[:100]}")
            except Exception as e:
                print(f"Error loading {vendor['company_name']}: {e}")


async def test_tenders():
    """Test tender matching"""
    print("\n Testing Tender Matching...")
    
    with open("data/sample/tenders.json", "r") as f:
        tenders = json.load(f)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for tender in tenders:
            try:
                response = await client.post(
                    f"{API_BASE}/matching/recommend?top_k=3", 
                    json=tender
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result['matches']:
                        top_match = result['matches'][0]
                        print(f"{tender['tender_title'][:50]}...")
                        print(f"   → {top_match['company_name']} ({top_match['match_percentage']}%)")
                    else:
                        print(f"No matches: {tender['tender_title'][:50]}...")
                else:
                    print(f"x Failed: {tender['tender_title'][:50]}...")
            except Exception as e:
                print(f"x Error: {tender['tender_title'][:40]}... - {e}")


async def main():
    print("="*70)
    print("LOADING SAMPLE DATA - UPDATED STRUCTURE")
    print("="*70)
    
    await load_vendors()
    await test_tenders()
    
    print("\n" + "="*70)
    print("SAMPLE DATA LOADED AND TESTED!")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
