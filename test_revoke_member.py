"""
Test Access API - Revoke Member
Test with user: testuser2@example.com
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import json
from django.test import Client
from django.contrib.auth import get_user_model
from uuid import uuid5, NAMESPACE_DNS

User = get_user_model()

# Setup test client
client = Client()

print("=" * 70)
print("Testing Access API - Revoke Member")
print("=" * 70)

# Login with testuser2
try:
    user = User.objects.get(username='testuser2@example.com')
    print(f"\n✓ Found user: {user.username} (ID: {user.id})")
except User.DoesNotExist:
    print("\n✗ User testuser2@example.com not found")
    exit(1)

client.force_login(user)
print("✓ User logged in")

# Get user's tenants
print("\n" + "="*70)
print("1. Get user's tenants")
print("="*70)
response = client.get('/api/tenants/')
data = response.json()
print(f"Status: {response.status_code}")

if data.get('success') and data.get('tenants'):
    tenants = data['tenants']
    print(f"Found {len(tenants)} tenants")
    tenant = tenants[0]
    tenant_id = tenant['id']
    print(f"Using tenant: {tenant['name']} (ID: {tenant_id})")
else:
    print("No tenants found or error")
    print(json.dumps(data, indent=2))
    exit(1)

# Get memberships for this tenant
print("\n" + "="*70)
print("2. Get tenant memberships")
print("="*70)
response = client.get(f'/api/access/memberships/?tenant_id={tenant_id}')
data = response.json()
print(f"Status: {response.status_code}")

if data.get('success') and data.get('memberships'):
    memberships = data['memberships']
    print(f"Found {len(memberships)} memberships")
    for m in memberships:
        print(f"  - Member: {m.get('email', 'N/A')} (ID: {m['id']}, Status: {m['status']})")
    
    # Find a membership to revoke (not the current user's admin membership)
    user_uuid = uuid5(NAMESPACE_DNS, f"user:{user.id}")
    test_membership = None
    for m in memberships:
        if m['user_id'] != str(user_uuid) or m['status'] == 'invited':
            test_membership = m
            break
    
    if not test_membership:
        print("\n⚠️ No suitable membership to revoke (need non-admin member)")
        print("Let's create an invited member first...")
        
        # Create invited member
        print("\n" + "="*70)
        print("3. Invite a test member")
        print("="*70)
        response = client.post(
            '/api/access/memberships/invite/',
            data=json.dumps({
                'tenant_id': tenant_id,
                'email': 'testmember@example.com',
                'role_slugs': ['member']
            }),
            content_type='application/json'
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        
        if data.get('success') and data.get('membership'):
            test_membership = data['membership']
            print(f"✓ Invited member: {test_membership.get('email')}")
            print(f"  Membership ID: {test_membership['id']}")
        else:
            print(f"✗ Failed to invite member: {data.get('error')}")
            print(json.dumps(data, indent=2))
            exit(1)
    
    # Now revoke the membership
    print("\n" + "="*70)
    print("4. Revoke membership")
    print("="*70)
    membership_id = test_membership['id']
    print(f"Revoking membership: {membership_id}")
    print(f"Member: {test_membership.get('email', 'N/A')}")
    
    response = client.post(f'/api/access/memberships/{membership_id}/revoke/')
    print(f"\nStatus: {response.status_code}")
    
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if data.get('success'):
            print(f"\n✓ SUCCESS: Membership revoked")
        else:
            print(f"\n✗ ERROR: {data.get('error')}")
    except Exception as e:
        print(f"✗ Failed to parse response: {e}")
        print(f"Raw response: {response.content.decode()}")
    
    # Verify membership is deleted
    print("\n" + "="*70)
    print("5. Verify membership is deleted")
    print("="*70)
    response = client.get(f'/api/access/memberships/?tenant_id={tenant_id}')
    data = response.json()
    
    if data.get('success') and data.get('memberships'):
        remaining = [m for m in data['memberships'] if m['id'] == membership_id]
        if not remaining:
            print(f"✓ Membership successfully deleted (not in list)")
        else:
            print(f"⚠️ Membership still exists with status: {remaining[0]['status']}")
    else:
        print("Could not verify")
        
else:
    print(f"✗ Failed to get memberships: {data.get('error')}")
    print(json.dumps(data, indent=2))

print("\n" + "="*70)
print("✓ Test completed")
print("="*70)
