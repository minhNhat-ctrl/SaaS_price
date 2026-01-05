#!/usr/bin/env python3
"""
API Testing Script for PriceSynC Backend

Usage:
    python3 test_api.py list-products
    python3 test_api.py create-product "Product Name"
    python3 test_api.py add-url <product_id> "https://amazon.co.jp/dp/..."
"""

import requests
import json
import sys
from typing import Optional, Dict, Any
from uuid import UUID

# Configuration
BASE_URL = "http://127.0.0.1:8005/api"
TENANT_ID = "07f93027-37f8-45cd-b97f-3872814a8ee9"
PRODUCT_ID = "f1c85b92-c245-4af3-889c-90a018ff49e2"

# Session for authentication
session = requests.Session()

# Colors for output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_request(method: str, url: str, data: Optional[Dict] = None):
    """Print request details."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}>>> {method} {url}{Colors.ENDC}")
    if data:
        print(f"{Colors.CYAN}{json.dumps(data, indent=2)}{Colors.ENDC}")

def print_response(response: requests.Response):
    """Print response details."""
    status_color = Colors.GREEN if response.ok else Colors.RED
    print(f"\n{Colors.BOLD}{status_color}<<< {response.status_code} {response.reason}{Colors.ENDC}")
    try:
        data = response.json()
        print(f"{json.dumps(data, indent=2)}")
        return data
    except:
        print(response.text)
        return None

def handle_error(err: Exception):
    """Handle and print errors."""
    print(f"\n{Colors.RED}{Colors.BOLD}✗ Error: {err}{Colors.ENDC}")
    sys.exit(1)

# ============================================================
# Authentication Operations
# ============================================================

def signup(email: str, password: str):
    """Register new user."""
    url = f"{BASE_URL}/identity/signup/"
    payload = {"email": email, "password": password}
    
    print_request("POST", url, payload)
    response = session.post(url, json=payload)
    data = print_response(response)
    return data

def login(email: str, password: str):
    """Login user."""
    url = f"{BASE_URL}/identity/login/"
    payload = {"email": email, "password": password}
    
    print_request("POST", url, payload)
    response = session.post(url, json=payload)
    data = print_response(response)
    return data

def logout():
    """Logout user."""
    url = f"{BASE_URL}/identity/logout/"
    
    print_request("POST", url)
    response = session.post(url)
    data = print_response(response)
    return data

def check_auth():
    """Check authentication status."""
    url = f"{BASE_URL}/identity/check-auth/"
    
    print_request("GET", url)
    response = session.get(url)
    data = print_response(response)
    return data

def change_password(new_password: str):
    """Change password (requires authenticated session)."""
    url = f"{BASE_URL}/identity/change-password/"
    payload = {"new_password": new_password}
    
    print_request("POST", url, payload)
    response = session.post(url, json=payload)
    data = print_response(response)
    return data

def request_email_verification(email: str):
    """Request email verification."""
    url = f"{BASE_URL}/identity/request-email-verification/"
    payload = {"email": email}
    
    print_request("POST", url, payload)
    response = session.post(url, json=payload)
    data = print_response(response)
    return data

def verify_email(token: str):
    """Verify email with token."""
    url = f"{BASE_URL}/identity/verify-email/"
    payload = {"token": token}
    
    print_request("POST", url, payload)
    response = session.post(url, json=payload)
    data = print_response(response)
    return data

def request_password_reset(email: str):
    """Request password reset."""
    url = f"{BASE_URL}/identity/request-password-reset/"
    payload = {"email": email}
    
    print_request("POST", url, payload)
    response = session.post(url, json=payload)
    data = print_response(response)
    return data

def reset_password(token: str, new_password: str):
    """Reset password with token."""
    url = f"{BASE_URL}/identity/reset-password/"
    payload = {"token": token, "new_password": new_password}
    
    print_request("POST", url, payload)
    response = session.post(url, json=payload)
    data = print_response(response)
    return data

def request_magic_link(email: str):
    """Request magic link for passwordless login."""
    url = f"{BASE_URL}/identity/request-magic-link/"
    payload = {"email": email}
    
    print_request("POST", url, payload)
    response = session.post(url, json=payload)
    data = print_response(response)
    return data

def magic_login(token: str):
    """Login with magic link token."""
    url = f"{BASE_URL}/identity/magic-login/"
    payload = {"token": token}
    
    print_request("POST", url, payload)
    response = session.post(url, json=payload)
    data = print_response(response)
    return data

# ============================================================
# Product CRUD Operations
# ============================================================

def list_products(status: Optional[str] = None):
    """List all products for tenant."""
    params = {"tenant_id": TENANT_ID}
    if status:
        params["status"] = status
    
    url = f"{BASE_URL}/products/"
    print_request("GET", url)
    
    response = session.get(f"{BASE_URL}/products/", params=params)
    data = print_response(response)
    return data

def create_product(name: str, sku: Optional[str] = None, gtin: Optional[str] = None, status: str = "ACTIVE"):
    """Create a new product."""
    url = f"{BASE_URL}/products/?tenant_id={TENANT_ID}"
    payload = {
        "name": name,
        "status": status
    }
    if sku:
        payload["sku"] = sku
    if gtin:
        payload["gtin"] = gtin
    
    print_request("POST", url, payload)
    response = session.post(f"{BASE_URL}/products/", json=payload, params={"tenant_id": TENANT_ID})
    data = print_response(response)
    return data

def get_product(product_id: str = PRODUCT_ID):
    """Get product details."""
    url = f"{BASE_URL}/products/{product_id}/?tenant_id={TENANT_ID}"
    print_request("GET", url)
    
    response = session.get(url.split('?')[0], params={"tenant_id": TENANT_ID})
    data = print_response(response)
    return data

def update_product(product_id: str, **kwargs):
    """Update product."""
    url = f"{BASE_URL}/products/{product_id}/?tenant_id={TENANT_ID}"
    payload = {k: v for k, v in kwargs.items() if v is not None}
    
    print_request("PATCH", url, payload)
    response = session.patch(url.split('?')[0], json=payload, params={"tenant_id": TENANT_ID})
    data = print_response(response)
    return data

def delete_product(product_id: str = PRODUCT_ID):
    """Delete product."""
    url = f"{BASE_URL}/products/{product_id}/?tenant_id={TENANT_ID}"
    print_request("DELETE", url)
    
    response = session.delete(url.split('?')[0], params={"tenant_id": TENANT_ID})
    data = print_response(response)
    return data

# ============================================================
# Product URL Operations
# ============================================================

def list_urls(product_id: str = PRODUCT_ID):
    """List all URLs for a product."""
    url = f"{BASE_URL}/products/{product_id}/urls/?tenant_id={TENANT_ID}"
    print_request("GET", url)
    
    response = session.get(url.split('?')[0], params={"tenant_id": TENANT_ID})
    data = print_response(response)
    return data

def add_url(product_id: str, raw_url: str, custom_label: str = "", is_primary: bool = False):
    """Add URL to product."""
    url = f"{BASE_URL}/products/{product_id}/urls/?tenant_id={TENANT_ID}"
    payload = {
        "raw_url": raw_url,
        "custom_label": custom_label,
        "is_primary": is_primary
    }
    
    print_request("POST", url, payload)
    response = session.post(url.split('?')[0], json=payload, params={"tenant_id": TENANT_ID})
    data = print_response(response)
    return data

def remove_url(product_id: str, url_hash: str):
    """Remove URL from product."""
    url = f"{BASE_URL}/products/{product_id}/urls/{url_hash}/?tenant_id={TENANT_ID}"
    print_request("DELETE", url)
    
    response = session.delete(url.split('?')[0], params={"tenant_id": TENANT_ID})
    data = print_response(response)
    return data

def get_prices(product_id: str = PRODUCT_ID, url_hash: Optional[str] = None):
    """Get price history."""
    params = {"tenant_id": TENANT_ID}
    if url_hash:
        params["url_hash"] = url_hash
    
    url = f"{BASE_URL}/products/{product_id}/prices/?tenant_id={TENANT_ID}"
    if url_hash:
        url += f"&url_hash={url_hash}"
    
    print_request("GET", url)
    response = session.get(f"{BASE_URL}/products/{product_id}/prices/", params=params)
    data = print_response(response)
    return data

def record_price(product_id: str, url_hash: str, price: float, currency: str = "JPY", is_available: bool = True):
    """Record a price."""
    url = f"{BASE_URL}/products/{product_id}/prices/?tenant_id={TENANT_ID}"
    payload = {
        "url_hash": url_hash,
        "price": price,
        "currency": currency,
        "is_available": is_available
    }
    
    print_request("POST", url, payload)
    response = session.post(url.split('?')[0], json=payload, params={"tenant_id": TENANT_ID})
    data = print_response(response)
    return data

# ============================================================
# Demo Scenarios
# ============================================================

def demo_auth_flow():
    """Run authentication demo flow."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== Authentication Flow Demo ==={Colors.ENDC}\n")
    
    test_email = "test-auth@example.com"
    test_password = "securepass123"
    
    # 1. Signup
    print(f"\n{Colors.BOLD}1. Signing up new user...{Colors.ENDC}")
    signup_result = signup(test_email, test_password)
    if signup_result and signup_result.get('success'):
        print(f"{Colors.GREEN}✓ Signup successful{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}⚠ User may already exist, continuing...{Colors.ENDC}")
    
    # 2. Login
    print(f"\n{Colors.BOLD}2. Logging in...{Colors.ENDC}")
    login_result = login(test_email, test_password)
    if login_result and login_result.get('success'):
        print(f"{Colors.GREEN}✓ Login successful{Colors.ENDC}")
    
    # 3. Check auth
    print(f"\n{Colors.BOLD}3. Checking authentication status...{Colors.ENDC}")
    auth_status = check_auth()
    if auth_status and auth_status.get('authenticated'):
        print(f"{Colors.GREEN}✓ User is authenticated{Colors.ENDC}")
    
    # 4. Request email verification
    print(f"\n{Colors.BOLD}4. Requesting email verification...{Colors.ENDC}")
    verify_request = request_email_verification(test_email)
    if verify_request:
        print(f"{Colors.GREEN}✓ Verification email sent (check console){Colors.ENDC}")
    
    # 5. Request magic link
    print(f"\n{Colors.BOLD}5. Requesting magic link...{Colors.ENDC}")
    magic_request = request_magic_link(test_email)
    if magic_request:
        print(f"{Colors.GREEN}✓ Magic link sent (check console){Colors.ENDC}")
    
    # 6. Request password reset
    print(f"\n{Colors.BOLD}6. Requesting password reset...{Colors.ENDC}")
    reset_request = request_password_reset(test_email)
    if reset_request:
        print(f"{Colors.GREEN}✓ Password reset email sent (check console){Colors.ENDC}")
    
    # 7. Logout
    print(f"\n{Colors.BOLD}7. Logging out...{Colors.ENDC}")
    logout_result = logout()
    if logout_result and logout_result.get('success'):
        print(f"{Colors.GREEN}✓ Logout successful{Colors.ENDC}")
    
    # 8. Check auth again
    print(f"\n{Colors.BOLD}8. Checking authentication status after logout...{Colors.ENDC}")
    auth_status = check_auth()
    if auth_status and not auth_status.get('authenticated'):
        print(f"{Colors.GREEN}✓ User is logged out{Colors.ENDC}")
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}=== Auth Demo Completed ==={Colors.ENDC}\n")
    print(f"{Colors.YELLOW}💡 Note: Check your console for email outputs (verification, magic link, password reset){Colors.ENDC}\n")

def demo_full_flow():
    """Run a complete demo flow."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== PriceSynC API Full Demo ==={Colors.ENDC}\n")
    
    # 1. Create product
    print(f"\n{Colors.BOLD}1. Creating product...{Colors.ENDC}")
    product = create_product(
        name="Sony WH-1000XM5 Headphones",
        sku="WH-1000XM5",
        gtin="4548736148896",
        status="ACTIVE"
    )
    if not product or not product.get('data'):
        handle_error("Failed to create product")
    
    product_id = product['data']['id']
    print(f"{Colors.GREEN}✓ Created product: {product_id}{Colors.ENDC}")
    
    # 2. Add URLs
    print(f"\n{Colors.BOLD}2. Adding URLs...{Colors.ENDC}")
    urls = [
        ("https://www.amazon.co.jp/dp/B0BW15NNJ2", "Amazon Japan"),
        ("https://www.rakuten.co.jp/shop/product", "Rakuten JP"),
    ]
    
    url_hashes = []
    for raw_url, label in urls:
        url_data = add_url(product_id, raw_url, label, is_primary=(label == "Amazon Japan"))
        if url_data and url_data.get('data') and url_data['data'].get('url'):
            url_hash = url_data['data']['url']['url_hash']
            url_hashes.append(url_hash)
            print(f"{Colors.GREEN}✓ Added URL: {label} -> {url_hash[:16]}...{Colors.ENDC}")
    
    # 3. List URLs
    print(f"\n{Colors.BOLD}3. Listing product URLs...{Colors.ENDC}")
    list_urls(product_id)
    
    # 4. Record prices
    if url_hashes:
        print(f"\n{Colors.BOLD}4. Recording prices...{Colors.ENDC}")
        for i, url_hash in enumerate(url_hashes[:1]):  # Record for first URL only
            record_price(product_id, url_hash, 39999 + (i * 1000), "JPY")
            print(f"{Colors.GREEN}✓ Recorded price for {url_hash[:16]}...{Colors.ENDC}")
    
    # 5. Get prices
    print(f"\n{Colors.BOLD}5. Getting price history...{Colors.ENDC}")
    get_prices(product_id)
    
    # 6. Update product
    print(f"\n{Colors.BOLD}6. Updating product...{Colors.ENDC}")
    update_product(product_id, status="DRAFT")
    
    # 7. Get product
    print(f"\n{Colors.BOLD}7. Getting product details...{Colors.ENDC}")
    get_product(product_id)
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}=== Demo Completed Successfully ==={Colors.ENDC}\n")

# ============================================================
# CLI Interface
# ============================================================

def main():
    if len(sys.argv) < 2:
        print(f"""
{Colors.BOLD}PriceSynC API Tester{Colors.ENDC}

Usage:
    python3 test_api.py <command> [args...]

Commands:
    {Colors.CYAN}Authentication:{Colors.ENDC}
        signup <email> <password>        Register new user
        login <email> <password>         Login user
        logout                           Logout current user
        check-auth                       Check authentication status
        change-password <new_password>   Change password (requires auth)
        request-email-verify <email>     Request email verification
        verify-email <token>             Verify email with token
        request-reset <email>            Request password reset
        reset-password <token> <password> Reset password with token
        request-magic <email>            Request magic link
        magic-login <token>              Login with magic link token
    
    {Colors.CYAN}Products:{Colors.ENDC}
        list-products [status]           List all products
        create-product <name> [sku] [gtin]  Create new product
        get-product [product_id]         Get product details
        update-product <product_id> [name] [sku] [status]  Update product
        delete-product [product_id]      Delete product
    
    {Colors.CYAN}URLs:{Colors.ENDC}
        list-urls [product_id]           List product URLs
        add-url <product_id> <url> [label] [primary]  Add URL to product
        remove-url <product_id> <url_hash>  Remove URL from product
    
    {Colors.CYAN}Prices:{Colors.ENDC}
        get-prices [product_id] [url_hash]  Get price history
        record-price <product_id> <url_hash> <price> [currency]  Record price
    
    {Colors.CYAN}Demo:{Colors.ENDC}
        demo-auth                        Run authentication demo
        demo                             Run full product demo

{Colors.YELLOW}Defaults:{Colors.ENDC}
    Tenant ID: {TENANT_ID}
    Product ID: {PRODUCT_ID}
""")
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        # Authentication commands
        if command == "signup":
            if len(sys.argv) < 4:
                print("Missing: email, password")
                sys.exit(1)
            signup(sys.argv[2], sys.argv[3])
        
        elif command == "login":
            if len(sys.argv) < 4:
                print("Missing: email, password")
                sys.exit(1)
            login(sys.argv[2], sys.argv[3])
        
        elif command == "logout":
            logout()
        
        elif command == "check-auth":
            check_auth()
        
        elif command == "change-password":
            if len(sys.argv) < 3:
                print("Missing: new_password")
                sys.exit(1)
            change_password(sys.argv[2])
        
        elif command == "request-email-verify":
            if len(sys.argv) < 3:
                print("Missing: email")
                sys.exit(1)
            request_email_verification(sys.argv[2])
        
        elif command == "verify-email":
            if len(sys.argv) < 3:
                print("Missing: token")
                sys.exit(1)
            verify_email(sys.argv[2])
        
        elif command == "request-reset":
            if len(sys.argv) < 3:
                print("Missing: email")
                sys.exit(1)
            request_password_reset(sys.argv[2])
        
        elif command == "reset-password":
            if len(sys.argv) < 4:
                print("Missing: token, new_password")
                sys.exit(1)
            reset_password(sys.argv[2], sys.argv[3])
        
        elif command == "request-magic":
            if len(sys.argv) < 3:
                print("Missing: email")
                sys.exit(1)
            request_magic_link(sys.argv[2])
        
        elif command == "magic-login":
            if len(sys.argv) < 3:
                print("Missing: token")
                sys.exit(1)
            magic_login(sys.argv[2])
        
        # Product commands
        elif command == "list-products":
            status = sys.argv[2] if len(sys.argv) > 2 else None
            list_products(status)
        
        elif command == "create-product":
            if len(sys.argv) < 3:
                print("Missing: product name")
                sys.exit(1)
            name = sys.argv[2]
            sku = sys.argv[3] if len(sys.argv) > 3 else None
            gtin = sys.argv[4] if len(sys.argv) > 4 else None
            create_product(name, sku, gtin)
        
        elif command == "get-product":
            product_id = sys.argv[2] if len(sys.argv) > 2 else PRODUCT_ID
            get_product(product_id)
        
        elif command == "update-product":
            if len(sys.argv) < 3:
                print("Missing: product_id")
                sys.exit(1)
            product_id = sys.argv[2]
            kwargs = {}
            if len(sys.argv) > 3:
                kwargs['name'] = sys.argv[3]
            if len(sys.argv) > 4:
                kwargs['sku'] = sys.argv[4]
            if len(sys.argv) > 5:
                kwargs['status'] = sys.argv[5]
            update_product(product_id, **kwargs)
        
        elif command == "delete-product":
            product_id = sys.argv[2] if len(sys.argv) > 2 else PRODUCT_ID
            delete_product(product_id)
        
        elif command == "list-urls":
            product_id = sys.argv[2] if len(sys.argv) > 2 else PRODUCT_ID
            list_urls(product_id)
        
        elif command == "add-url":
            if len(sys.argv) < 4:
                print("Missing: product_id, url")
                sys.exit(1)
            product_id = sys.argv[2]
            raw_url = sys.argv[3]
            custom_label = sys.argv[4] if len(sys.argv) > 4 else ""
            is_primary = sys.argv[5].lower() == 'true' if len(sys.argv) > 5 else False
            add_url(product_id, raw_url, custom_label, is_primary)
        
        elif command == "remove-url":
            if len(sys.argv) < 4:
                print("Missing: product_id, url_hash")
                sys.exit(1)
            product_id = sys.argv[2]
            url_hash = sys.argv[3]
            remove_url(product_id, url_hash)
        
        elif command == "get-prices":
            product_id = sys.argv[2] if len(sys.argv) > 2 else PRODUCT_ID
            url_hash = sys.argv[3] if len(sys.argv) > 3 else None
            get_prices(product_id, url_hash)
        
        elif command == "record-price":
            if len(sys.argv) < 5:
                print("Missing: product_id, url_hash, price")
                sys.exit(1)
            product_id = sys.argv[2]
            url_hash = sys.argv[3]
            price = float(sys.argv[4])
            currency = sys.argv[5] if len(sys.argv) > 5 else "JPY"
            record_price(product_id, url_hash, price, currency)
        
        elif command == "demo-auth":
            demo_auth_flow()
        
        elif command == "demo":
            demo_full_flow()
        
        else:
            print(f"{Colors.RED}Unknown command: {command}{Colors.ENDC}")
            sys.exit(1)
    
    except Exception as e:
        handle_error(e)

if __name__ == "__main__":
    main()
