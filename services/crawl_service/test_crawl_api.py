#!/usr/bin/env python
"""
Crawl Service API Testing Script

Usage:
    python test_crawl_api.py test_pull
    python test_crawl_api.py test_submit
    python test_crawl_api.py test_full
"""

import os
import sys
import json
import django
import requests
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/var/www/PriceSynC/Saas_app')
django.setup()

from services.crawl_service.models import CrawlJob, CrawlTask, CrawlResult, ScheduleRule


API_BASE_URL = "http://localhost:8000/api/crawl"


class CrawlServiceTester:
    """Test crawl service API endpoints"""
    
    def __init__(self):
        self.base_url = API_BASE_URL
        print(f"🤖 Crawl Service API Tester")
        print(f"📍 Base URL: {self.base_url}")
        print("-" * 60)
    
    def setup_test_data(self):
        """Create test schedule rule and jobs"""
        print("\n📝 Setting up test data...")
        
        # Create schedule rule
        rule, created = ScheduleRule.objects.get_or_create(
            name="Test Schedule",
            defaults={
                'description': "For testing",
                'enabled': True,
                'cron_expression': "0 * * * *",
                'priority': 5,
                'max_retries': 3,
                'timeout_minutes': 10,
            }
        )
        print(f"  ✓ Schedule Rule: {rule.name} (id={rule.id})")
        
        # Create test jobs
        urls = [
            "https://example.com/product-1",
            "https://example.com/product-2",
            "https://example.com/product-3",
        ]
        
        for url in urls:
            job, created = CrawlJob.objects.get_or_create(
                url=url,
                defaults={
                    'status': 'pending',
                    'schedule_rule': rule,
                    'priority': 5,
                    'max_retries': 3,
                    'timeout_minutes': 10,
                    'next_run_at': datetime.now()
                }
            )
            if created:
                print(f"  ✓ Created Job: {url}")
            else:
                print(f"  ✓ Job exists: {url}")
        
        return rule
    
    def test_pull(self):
        """Test bot pulling tasks"""
        print("\n\n🔄 TEST 1: Bot Pull Tasks")
        print("-" * 60)
        
        payload = {
            "bot_id": "test-bot-001",
            "max_tasks": 5
        }
        
        print(f"\n📤 Request: POST {self.base_url}/pull/")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(
                f"{self.base_url}/pull/",
                json=payload,
                timeout=10
            )
            
            print(f"\n📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ SUCCESS")
                print(f"Response:\n{json.dumps(data, indent=2)}")
                
                if data.get('tasks'):
                    print(f"\n📊 Got {len(data['tasks'])} tasks:")
                    for task in data['tasks']:
                        print(f"  • Task {task['task_id'][:8]}... → {task['url']}")
                        print(f"    Timeout: {task['timeout_at']}")
                
                return data['tasks'][0]['task_id'] if data.get('tasks') else None
            else:
                print(f"\n❌ FAILED")
                print(f"Response:\n{response.text}")
                return None
        
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            return None
    
    def test_submit(self, task_id):
        """Test bot submitting results"""
        print("\n\n📤 TEST 2: Bot Submit Result")
        print("-" * 60)
        
        if not task_id:
            # Get a task from database
            task = CrawlTask.objects.filter(status='assigned').first()
            if not task:
                print("❌ No assigned tasks. Run test_pull first.")
                return False
            task_id = str(task.id)
        
        payload = {
            "task_id": task_id,
            "bot_id": "test-bot-001",
            "price": 49.99,
            "currency": "USD",
            "title": "Test Product Name",
            "in_stock": True,
            "parsed_data": {
                "rating": 4.5,
                "reviews": 120,
                "shipping": "Free"
            }
        }
        
        print(f"\n📤 Request: POST {self.base_url}/submit/")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(
                f"{self.base_url}/submit/",
                json=payload,
                timeout=10
            )
            
            print(f"\n📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ SUCCESS")
                print(f"Response:\n{json.dumps(data, indent=2)}")
                
                # Show created result
                if data.get('result_id'):
                    result = CrawlResult.objects.get(id=data['result_id'])
                    print(f"\n📊 Result Details:")
                    print(f"  • Price: {result.price} {result.currency}")
                    print(f"  • Title: {result.title}")
                    print(f"  • In Stock: {result.in_stock}")
                    print(f"  • Parsed Data: {result.parsed_data}")
                
                return True
            else:
                print(f"\n❌ FAILED")
                print(f"Response:\n{response.text}")
                return False
        
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            return False
    
    def test_full_flow(self):
        """Test complete pull → submit flow"""
        print("\n\n🔗 TEST 3: Full Workflow (Pull → Submit)")
        print("-" * 60)
        
        print("\nStep 1️⃣  Pull task from scheduler...")
        task_id = self.test_pull()
        
        if not task_id:
            print("❌ Failed to pull task. Aborting.")
            return
        
        print("\nStep 2️⃣  Submit result back...")
        self.test_submit(task_id)
        
        print("\n\n✅ Full workflow complete!")
    
    def show_status(self):
        """Show current database status"""
        print("\n\n📊 Database Status")
        print("-" * 60)
        
        pending = CrawlJob.objects.filter(status='pending').count()
        running = CrawlJob.objects.filter(status='running').count()
        completed = CrawlJob.objects.filter(status='completed').count()
        failed = CrawlJob.objects.filter(status='failed').count()
        
        queued_tasks = CrawlTask.objects.filter(status='queued').count()
        assigned_tasks = CrawlTask.objects.filter(status='assigned').count()
        completed_tasks = CrawlTask.objects.filter(status='completed').count()
        
        results = CrawlResult.objects.count()
        
        print(f"\n📌 Jobs:")
        print(f"  • Pending:   {pending}")
        print(f"  • Running:   {running}")
        print(f"  • Completed: {completed}")
        print(f"  • Failed:    {failed}")
        
        print(f"\n📋 Tasks:")
        print(f"  • Queued:    {queued_tasks}")
        print(f"  • Assigned:  {assigned_tasks}")
        print(f"  • Completed: {completed_tasks}")
        
        print(f"\n🎯 Results:")
        print(f"  • Total Results: {results}")
        
        if results > 0:
            latest = CrawlResult.objects.latest('created_at')
            print(f"  • Latest: {latest.job.url}")
            print(f"    Price: {latest.price} {latest.currency}")


def main():
    tester = CrawlServiceTester()
    
    # Setup test data
    tester.setup_test_data()
    tester.show_status()
    
    # Run tests
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'test_pull':
            tester.test_pull()
        elif command == 'test_submit':
            tester.test_submit(None)
        elif command == 'test_full':
            tester.test_full_flow()
        elif command == 'status':
            tester.show_status()
        else:
            print(f"Unknown command: {command}")
            print("\nUsage:")
            print("  python test_crawl_api.py test_pull      # Test pulling tasks")
            print("  python test_crawl_api.py test_submit    # Test submitting results")
            print("  python test_crawl_api.py test_full      # Test full workflow")
            print("  python test_crawl_api.py status         # Show database status")
    else:
        print("\nUsage:")
        print("  python test_crawl_api.py test_pull      # Test pulling tasks")
        print("  python test_crawl_api.py test_submit    # Test submitting results")
        print("  python test_crawl_api.py test_full      # Test full workflow")
        print("  python test_crawl_api.py status         # Show database status")


if __name__ == '__main__':
    main()
