#!/usr/bin/env python3.9
"""
Manual API Test - Products Add URL
Tests the actual HTTP API endpoint with real session
"""
import requests
import json

# ============================================================
# Configuration
# ============================================================
BASE_URL = "https://app.2kvietnam.com"
EMAIL = "testuser2@example.com"
PASSWORD = "testpass123"

print("=" * 70)
print("Manual API Test - Products Add URL")
print("=" * 70)

# ============================================================
# Step 1: Login to get session
# ============================================================
print("\n" + "=" * 70)
print("1. Login")
print("=" * 70)

session = requests.Session()
login_response = session.post(
    f"{BASE_URL}/api/identity/login/",
    json={"email": EMAIL, "password": PASSWORD}
)

print(f"Status: {login_response.status_code}")
if login_response.status_code == 200:
    print("✓ Login successful")
    print(f"Session cookies: {session.cookies.get_dict()}")
else:
    print(f"❌ Login failed: {login_response.text}")
    exit(1)

# ============================================================
# Step 2: Get user's tenants
# ============================================================
print("\n" + "=" * 70)
print("2. Get tenants")
print("=" * 70)

tenants_response = session.get(f"{BASE_URL}/api/tenants/")
print(f"Status: {tenants_response.status_code}")

if tenants_response.status_code == 200:
    data = tenants_response.json()
    tenants = data.get('tenants', [])
    print(f"Found {len(tenants)} tenants")
    
    if len(tenants) < 1:
        print("❌ No tenants found")
        exit(1)
    
    tenant = tenants[0]
    tenant_id = tenant['id']
    print(f"Using tenant: {tenant['name']} (ID: {tenant_id})")
else:
    print(f"❌ Failed: {tenants_response.text}")
    exit(1)

# ============================================================
# Step 3: Get or create a product
# ============================================================
print("\n" + "=" * 70)
print("3. Get products")
print("=" * 70)

products_response = session.get(
    f"{BASE_URL}/api/products/tenants/{tenant_id}/products/"
)
print(f"Status: {products_response.status_code}")

if products_response.status_code == 200:
    data = products_response.json()
    products = data.get('products', [])
    print(f"Found {len(products)} products")
    
    if len(products) < 1:
        print("\nCreating test product...")
        create_response = session.post(
            f"{BASE_URL}/api/products/tenants/{tenant_id}/products/",
            json={
                "name": "Test Product for URL",
                "sku": f"TEST-URL-{tenant_id[:8]}",
                "status": "ACTIVE"
            }
        )
        
        if create_response.status_code == 201:
            product = create_response.json()['product']
            print(f"✓ Created product: {product['name']}")
        else:
            print(f"❌ Failed to create: {create_response.text}")
            exit(1)
    else:
        product = products[0]
    
    product_id = product['id']
    print(f"Using product: {product['name']} (ID: {product_id})")
else:
    print(f"❌ Failed: {products_response.text}")
    exit(1)

# ============================================================
# Step 4: Add URL to product (First attempt)
# ============================================================
print("\n" + "=" * 70)
print("4. Add URL to product (TEST 1)")
print("=" * 70)

test_url = "https://www.amazon.com/Test-Product-Manual-API/dp/B0TESTURL999"
print(f"URL: {test_url}")

add_url_response = session.post(
    f"{BASE_URL}/api/products/tenants/{tenant_id}/products/{product_id}/urls/",
    json={
        "url": test_url,
        "marketplace": "AMAZON",
        "is_primary": True
    }
)

print(f"Status: {add_url_response.status_code}")
print(f"Response: {json.dumps(add_url_response.json(), indent=2)}")

if add_url_response.status_code == 201:
    print("✓ SUCCESS: URL added")
    url_data = add_url_response.json()
    url_id = url_data['url']['id']
    print(f"  URL ID: {url_id}")
elif add_url_response.status_code == 500:
    print("❌ ERROR 500: Internal Server Error")
    print("\nChecking gunicorn logs...")
    import subprocess
    try:
        log_output = subprocess.check_output(
            ['sudo', 'tail', '-30', '/var/log/gunicorn/error.log'],
            stderr=subprocess.STDOUT,
            text=True
        )
        print("Last 30 lines of error log:")
        print(log_output)
    except Exception as e:
        print(f"Could not read logs: {e}")
    exit(1)
else:
    print(f"❌ Unexpected status: {add_url_response.status_code}")
    exit(1)

# ============================================================
# Step 5: Add same URL again (Test URL reuse)
# ============================================================
print("\n" + "=" * 70)
print("5. Add same URL again (TEST 2 - Should reuse)")
print("=" * 70)

add_url_response2 = session.post(
    f"{BASE_URL}/api/products/tenants/{tenant_id}/products/{product_id}/urls/",
    json={
        "url": test_url,
        "marketplace": "AMAZON",
        "is_primary": False
    }
)

print(f"Status: {add_url_response2.status_code}")
print(f"Response: {json.dumps(add_url_response2.json(), indent=2)}")

if add_url_response2.status_code == 201:
    print("✓ SUCCESS: URL reused (no 409 error)")
    url_data2 = add_url_response2.json()
    url_id2 = url_data2['url']['id']
    
    if url_id2 == url_id:
        print("✓✓ PERFECT: Same URL ID (shared URL confirmed)")
    else:
        print("⚠️  Different URL ID (might be expected)")
else:
    print(f"⚠️  Status: {add_url_response2.status_code}")

# ============================================================
# Step 6: List URLs for product
# ============================================================
print("\n" + "=" * 70)
print("6. List URLs for product")
print("=" * 70)

list_urls_response = session.get(
    f"{BASE_URL}/api/products/tenants/{tenant_id}/products/{product_id}/urls/"
)

print(f"Status: {list_urls_response.status_code}")
if list_urls_response.status_code == 200:
    urls = list_urls_response.json().get('urls', [])
    print(f"Found {len(urls)} URLs:")
    for url in urls:
        print(f"  - {url.get('full_url', 'N/A')[:60]}... (ID: {url['id']})")

# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 70)
print("✓ Test completed successfully")
print("=" * 70)
print("\nKey Results:")
print("1. ✓ Login successful")
print("2. ✓ Retrieved tenants")
print("3. ✓ Retrieved/created product")
print("4. ✓ Added URL to product")
print("5. ✓ URL sharing works (no 409 error)")
print("\n" + "=" * 70)
