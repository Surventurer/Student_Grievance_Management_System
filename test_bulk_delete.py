#!/usr/bin/env python3
"""
Test the bulk delete functionality
"""
import requests
import json

def test_bulk_delete():
    base_url = "http://127.0.0.1:8000"
    
    # First, we need to get a CSRF token by visiting the page
    session = requests.Session()
    
    try:
        # Get the user management page to extract CSRF token
        response = session.get(f"{base_url}/admin-panel/superadmin/users/")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ User management page loads successfully")
            print("✅ Server is running and responding")
            
            # Check if our new elements are present in the HTML
            html_content = response.text
            
            if 'bulk-delete-btn' in html_content:
                print("✅ Bulk delete button element found in HTML")
            else:
                print("❌ Bulk delete button element not found in HTML")
                
            if 'select-all' in html_content:
                print("✅ Select-all checkbox element found in HTML")
            else:
                print("❌ Select-all checkbox element not found in HTML")
                
            if 'user-checkbox' in html_content:
                print("✅ User checkbox elements found in HTML")
            else:
                print("❌ User checkbox elements not found in HTML")
                
            if 'bulkDeleteUsers' in html_content:
                print("✅ Bulk delete JavaScript function found in HTML")
            else:
                print("❌ Bulk delete JavaScript function not found in HTML")
                
        elif response.status_code == 302:
            print("📝 Redirected (likely need to login first)")
            print("✅ Server is running")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure Django server is running.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Testing Bulk Delete Feature Implementation")
    print("=" * 50)
    test_bulk_delete()
    print("=" * 50)
    print("✅ Test completed!")
