import requests
import json

# URL for the load_departments endpoint - adjust if needed to match your local server
base_url = "http://localhost:8000"
url = f"{base_url}/auth/load-departments/"  # Updated URL path

# Test with a specific school ID
school_id = 10  # School of Engineering

# Make the request
print(f"Testing endpoint {url} with school_id={school_id}")
response = requests.get(url, params={"school_id": school_id})

# Check the response
print(f"Response status code: {response.status_code}")
try:
    data = response.json()
    print("Response data:", json.dumps(data, indent=2))
    
    # Check if departments were returned
    if "departments" in data:
        print(f"Found {len(data['departments'])} departments for school ID {school_id}")
        for i, dept in enumerate(data["departments"], 1):
            print(f"{i}. Department ID: {dept.get('id')}, Name: {dept.get('name')}")
    else:
        print("No departments key in response")
except Exception as e:
    print(f"Error parsing JSON response: {e}")
    print("Raw response:", response.text)
