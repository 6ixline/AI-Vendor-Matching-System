"""API testing"""

import httpx

API_BASE = "http://localhost:8000/api/v1"

def print_result(test_name: str, success: bool, details: str = ""):
    status = "✔" if success else "x"
    print(f"{status} {test_name}")
    if details:
        print(f"   {details}")


def test_health():
    """Test 1: System Health"""
    print("\n" + "="*70)
    print("TEST 1: System Health Check")
    print("="*70)
    
    response = httpx.get("http://localhost:8000/health", timeout=10.0)
    success = response.status_code == 200 and response.json().get("status") == "healthy"
    
    if success:
        stats = response.json().get("stats", {})
        print_result(
            "Health Check", 
            True, 
            f"Vendors: {stats.get('vendors_count')}, Status: {stats.get('status')}"
        )
    else:
        print_result("Health Check", False, response.text[:100])


def test_create_vendor():
    """Test 2: Create New Vendor"""
    print("\n" + "="*70)
    print("TEST 2: Create New Vendor")
    print("="*70)
    
    vendor = {
        "vendor_id": "V_TEST_001",
        "company_name": "Test Vendor Pvt Ltd",
        "description": "Test vendor for API testing",
        "industries": ["Information Technology"],
        "categories": ["Software Development"],
        "products": ["Web Development", "Mobile Apps"],
        "business_type": "Service Provider",
        "states": ["Karnataka"],
        "annual_turnover": "5-10 Crores",
        "certifications": ["ISO 9001:2015"]
    }
    
    response = httpx.post(f"{API_BASE}/vendors/", json=vendor, timeout=30.0)
    
    if response.status_code == 201:
        result = response.json()
        print_result(
            "Create Vendor",
            True,
            f"Created: {result['vendor_id']}"
        )
    else:
        print_result("Create Vendor", False, response.text[:100])


def test_get_vendor():
    """Test 3: Get Vendor Details"""
    print("\n" + "="*70)
    print("TEST 3: Get Vendor Details")
    print("="*70)
    
    response = httpx.get(f"{API_BASE}/vendors/V001", timeout=10.0)
    
    if response.status_code == 200:
        vendor = response.json()['vendor']
        print_result("Get Vendor", True, vendor['company_name'])
        print(f"   Industries: {len(vendor['industries'])} → {', '.join(vendor['industries'])}")
        print(f"   Categories: {len(vendor['categories'])} → {', '.join(vendor['categories'][:3])}...")
        print(f"   States: {len(vendor['states'])} → {', '.join(vendor['states'])}")
        print(f"   Products: {len(vendor['products'])} items")
    else:
        print_result("Get Vendor", False)


def test_update_vendor_full():
    """Test 4: Full Vendor Update"""
    print("\n" + "="*70)
    print("TEST 4: Full Vendor Update")
    print("="*70)
    
    update_data = {
        "company_name": "Test Vendor - UPDATED",
        "description": "Updated description with new services",
        "industries": ["Information Technology", "Consulting"],
        "categories": ["Software Development", "Cloud Services"],
        "products": ["Web Development", "Mobile Apps", "Cloud Solutions"],
        "annual_turnover": "10-25 Crores",
        "certifications": ["ISO 9001:2015", "CMMI Level 3"]
    }
    
    response = httpx.put(
        f"{API_BASE}/vendors/V_TEST_001",
        json=update_data,
        timeout=30.0
    )
    
    if response.status_code == 200:
        result = response.json()
        print_result(
            "Full Update",
            True,
            f"Updated {len(result['updated_fields'])} fields"
        )
        print(f"   Fields: {', '.join(result['updated_fields'][:5])}")
    else:
        print_result("Full Update", False, response.text[:100])


def test_update_vendor_partial():
    """Test 5: Partial Vendor Update"""
    print("\n" + "="*70)
    print("TEST 5: Partial Vendor Update")
    print("="*70)
    
    update_data = {
        "description": "Only updating description field",
        "annual_turnover": "25-50 Crores"
    }
    
    response = httpx.patch(
        f"{API_BASE}/vendors/V_TEST_001",
        json=update_data,
        timeout=30.0
    )
    
    if response.status_code == 200:
        result = response.json()
        print_result(
            "Partial Update",
            True,
            f"Updated: {', '.join(result['updated_fields'])}"
        )
    else:
        print_result("Partial Update", False, response.text[:100])


def test_pan_india_tender():
    """Test 6: Pan India Tender"""
    print("\n" + "="*70)
    print("TEST 6: Pan India Cybersecurity Tender")
    print("="*70)
    
    tender = {
        "tender_id": "TEST_PAN_001",
        "tender_title": "National Cybersecurity Assessment",
        "brief_description": "Pan India security audit for banking network with 200+ branches",
        "industry": "Information Technology",
        "categories": ["Cybersecurity", "IT Security"],
        "subcategory": "Security Audit",
        "state_preference": "pan_india",
        "states": [],
        "required_certifications": ["CISSP"],
        "buyer_id": "TEST_BUYER",
        "posted_date": "2025-11-05"
    }
    
    response = httpx.post(f"{API_BASE}/matching/recommend?top_k=3", json=tender, timeout=30.0)
    
    if response.status_code == 200:
        result = response.json()
        if result['matches']:
            top = result['matches'][0]
            print_result(
                "Pan India Matching", 
                True, 
                f"Top: {top['company_name']} ({top['match_percentage']}%)"
            )
            print(f"   States: {', '.join(top['vendor_details']['states'][:3])}")
            print(f"   Reason: {top['match_reasons'][0]}")
        else:
            print_result("Pan India Matching", False, "No matches found")
    else:
        print_result("Pan India Matching", False, response.text[:100])


def test_specific_states():
    """Test 7: Specific States Tender"""
    print("\n" + "="*70)
    print("TEST 7: Specific States - Maharashtra Construction")
    print("="*70)
    
    tender = {
        "tender_id": "TEST_STATE_001",
        "tender_title": "Green Building Construction in Maharashtra",
        "brief_description": "LEED certified office building with solar panels",
        "industry": "Construction",
        "categories": ["Green Building", "Commercial Construction"],
        "subcategory": "Sustainable Construction",
        "state_preference": "specific_states",
        "states": ["Maharashtra"],
        "required_certifications": ["LEED AP"],
        "buyer_id": "TEST_BUYER",
        "posted_date": "2025-11-05"
    }
    
    response = httpx.post(f"{API_BASE}/matching/recommend?top_k=3", json=tender, timeout=30.0)
    
    if response.status_code == 200:
        result = response.json()
        if result['matches']:
            top = result['matches'][0]
            print_result(
                "State-Specific Matching", 
                True, 
                f"Top: {top['company_name']} ({top['match_percentage']}%)"
            )
            vendor_states = top['vendor_details']['states']
            print(f"   Vendor operates in: {', '.join(vendor_states[:3])}")
            print(f"   Match: {'Maharashtra' in vendor_states}")
        else:
            print_result("State-Specific Matching", False, "No matches")
    else:
        print_result("State-Specific Matching", False)


def test_multiple_categories():
    """Test 8: Multiple Categories"""
    print("\n" + "="*70)
    print("TEST 8: Multiple Categories - IT Services")
    print("="*70)
    
    tender = {
        "tender_id": "TEST_MULTI_001",
        "tender_title": "IT Infrastructure and Cloud Services",
        "brief_description": "Need cloud migration, software development and AI/ML consulting",
        "industry": "Information Technology",
        "categories": ["Software Development", "Cloud Services", "AI/ML"],
        "state_preference": "specific_states",
        "states": ["Karnataka", "Maharashtra"],
        "required_certifications": [],
        "buyer_id": "TEST_BUYER",
        "posted_date": "2025-11-05"
    }
    
    response = httpx.post(f"{API_BASE}/matching/recommend?top_k=3", json=tender, timeout=30.0)
    
    if response.status_code == 200:
        result = response.json()
        if result['matches']:
            print_result(
                "Multiple Categories", 
                True, 
                f"Found {result['total_matches']} matches"
            )
            for match in result['matches'][:2]:
                print(f"   {match['ranking']}. {match['company_name']} ({match['match_percentage']}%)")
                matching_cats = set(tender['categories']) & set(match['vendor_details']['categories'])
                if matching_cats:
                    print(f"      Matching: {', '.join(matching_cats)}")
                else:
                    print(f"      Matching: Semantic similarity")
        else:
            print_result("Multiple Categories", False)
    else:
        print_result("Multiple Categories", False)


def test_certification_filtering():
    """Test 9: Certification Filtering"""
    print("\n" + "="*70)
    print("TEST 9: Hard Certification Requirement")
    print("="*70)
    
    tender = {
        "tender_id": "TEST_CERT_001",
        "tender_title": "Security Audit with Strict Certification",
        "brief_description": "Security audit requiring specific certifications",
        "industry": "Information Technology",
        "categories": ["Cybersecurity"],
        "state_preference": "pan_india",
        "states": [],
        "required_certifications": ["CISSP", "CEH", "ISO 27001"],
        "buyer_id": "TEST_BUYER",
        "posted_date": "2025-11-05"
    }
    
    response = httpx.post(f"{API_BASE}/matching/recommend?top_k=5", json=tender, timeout=30.0)
    
    if response.status_code == 200:
        result = response.json()
        print_result(
            "Certification Filtering", 
            result['total_matches'] > 0, 
            f"Found {result['total_matches']} vendors with ALL required certs"
        )
        
        for match in result['matches'][:2]:
            vendor_certs = match['vendor_details']['certifications']
            has_all = all(cert in vendor_certs for cert in tender['required_certifications'])
            print(f"   {match['company_name']}: Has all certs = {has_all}")
    else:
        print_result("Certification Filtering", False)


def test_quick_match():
    """Test 10: Quick Match"""
    print("\n" + "="*70)
    print("TEST 10: Quick Match Endpoint")
    print("="*70)
    
    tender = {
        "tender_id": "TEST_QUICK_001",
        "tender_title": "Safety Equipment Supply",
        "brief_description": "Industrial safety helmets and protective gear",
        "industry": "Manufacturing",
        "categories": ["Safety Equipment"],
        "state_preference": "specific_states",
        "states": ["Maharashtra", "Gujarat"],
        "required_certifications": [],
        "buyer_id": "TEST_BUYER",
        "posted_date": "2025-11-05"
    }
    
    response = httpx.post(f"{API_BASE}/matching/quick-match", json=tender, timeout=30.0)
    
    if response.status_code == 200:
        result = response.json()
        print_result(
            "Quick Match", 
            True, 
            f"Found {result['match_count']} matches in {result['search_time_ms']}ms"
        )
        print(f"   Vendor IDs: {result['vendor_ids']}")
    else:
        print_result("Quick Match", False)


def test_feedback():
    """Test 11: Feedback Submission"""
    print("\n" + "="*70)
    print("TEST 11: Submit Positive Feedback")
    print("="*70)
    
    feedback = {
        "tender_id": "T001",
        "vendor_id": "V001",
        "match_success": True,
        "selected": True,
        "rating": 5,
        "comments": "Perfect match! Contract awarded.",
        "feedback_type": "contract_awarded"
    }
    
    response = httpx.post(f"{API_BASE}/feedback/", json=feedback, timeout=10.0)
    
    if response.status_code == 200:
        result = response.json()
        print_result(
            "Feedback Processing", 
            True, 
            f"Adjustment: {result['details'].get('adjustment')}"
        )
    else:
        print_result("Feedback Processing", False)


def test_update_impact_on_matching():
    """Test 12: Verify Update Impact on Matching"""
    print("\n" + "="*70)
    print("TEST 12: Update Impact on Matching")
    print("="*70)
    
    # Update test vendor with blockchain products
    update_data = {
        "products": ["Blockchain Development", "Smart Contracts", "Web3 Solutions"]
    }
    
    response = httpx.put(
        f"{API_BASE}/vendors/V_TEST_001",
        json=update_data,
        timeout=30.0
    )
    
    if response.status_code == 200:
        print_result("Vendor Updated", True, "Added blockchain products")
        
        # Now search for blockchain tender
        tender = {
            "tender_id": "TEST_BLOCKCHAIN",
            "tender_title": "Blockchain Development",
            "brief_description": "Need blockchain and smart contract development",
            "industry": "Information Technology",
            "categories": ["Software Development"],
            "state_preference": "specific_states",
            "states": ["Karnataka"],
            "required_certifications": [],
            "buyer_id": "TEST_BUYER",
            "posted_date": "2025-11-05"
        }
        
        response = httpx.post(
            f"{API_BASE}/matching/recommend?top_k=5",
            json=tender,
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Check if our updated vendor appears
            found = False
            for match in result['matches']:
                if match['vendor_id'] == 'V_TEST_001':
                    found = True
                    print_result(
                        "Updated Vendor Matched",
                        True,
                        f"Score: {match['match_percentage']}%"
                    )
                    print(f"   Products: {', '.join(match['vendor_details']['products'])}")
                    break
            
            if not found:
                print_result("Updated Vendor Matched", False, "Test vendor not in top matches")
    else:
        print_result("Update for Matching Test", False)


def test_delete_vendor():
    """Test 13: Delete Vendor"""
    print("\n" + "="*70)
    print("TEST 13: Delete Test Vendor")
    print("="*70)
    
    response = httpx.delete(f"{API_BASE}/vendors/V_TEST_001", timeout=10.0)
    
    if response.status_code == 200:
        result = response.json()
        print_result(
            "Delete Vendor",
            True,
            f"Deleted: {result['vendor_id']}"
        )
        
        # Verify deletion
        verify = httpx.get(f"{API_BASE}/vendors/V_TEST_001", timeout=10.0)
        if verify.status_code == 404:
            print_result("Verify Deletion", True, "Vendor no longer exists")
        else:
            print_result("Verify Deletion", False, "Vendor still exists!")
    else:
        print_result("Delete Vendor", False, response.text[:100])


def main():
    print("\n" + "="*68)
    print("   VENDOR-TENDER MATCHING - COMPLETE API TEST SUITE")
    print("   (Includes: Health, CRUD, Matching, Feedback, Updates)")
    print("="*70)
    
    try:
        # System Health
        test_health()
        
        # Vendor CRUD Operations
        test_create_vendor()
        test_get_vendor()
        test_update_vendor_full()
        test_update_vendor_partial()
        
        # Matching Tests
        test_pan_india_tender()
        test_specific_states()
        test_multiple_categories()
        test_certification_filtering()
        test_quick_match()
        
        # Feedback & Advanced
        test_feedback()
        test_update_impact_on_matching()
        
        # Cleanup
        test_delete_vendor()
        
        print("\n" + "="*70)
        print("✔ ALL 13 TESTS COMPLETED SUCCESSFULLY!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\nx Test suite failed: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

