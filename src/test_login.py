"""
Test script to verify CS Officer login flow
"""
import requests

def test_login():
    base_url = "http://127.0.0.1:8000"
    
    # Test CS Officer login
    print("Testing CS Officer login...")
    
    # Get login page to get CSRF token
    login_url = f"{base_url}/auth/login/"
    session = requests.Session()
    
    try:
        response = session.get(login_url)
        print(f"Login page status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Login page accessible")
        else:
            print("❌ Login page not accessible")
            
    except requests.exceptions.ConnectionError:
        print("❌ Server not running or not accessible")
        print("Make sure the Django server is running at http://127.0.0.1:8000")

if __name__ == "__main__":
    test_login()
