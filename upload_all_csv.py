"""
Quick script to upload all CSV files to the database
Run this to populate the database with all depot data
"""

import requests
import os

# Configuration
API_BASE_URL = "http://localhost:8000/api"
# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# CSV_DATA is one level up from backend directory
CSV_DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "CSV_DATA")

# Files to upload in order (order matters due to foreign key constraints)
FILES_TO_UPLOAD = [
    ("depots", "depots.csv"),
    ("stops", "stops.csv"),
    ("routes", "routes.csv"),
    ("vehicles", "vehicles.csv"),
    ("drivers", "drivers.csv"),
    ("timetable", "timetable.csv"),
]

def upload_csv(data_type, file_path):
    """Upload a CSV file to the backend"""
    print(f"\n{'='*60}")
    print(f"Uploading {data_type}...")
    print(f"File: {file_path}")
    print(f"{'='*60}")
    
    if not os.path.exists(file_path):
        print(f"❌ ERROR: File not found: {file_path}")
        return False
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'text/csv')}
            response = requests.post(
                f"{API_BASE_URL}/data/upload/{data_type}",
                files=files,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SUCCESS: Uploaded {result.get('records_inserted', 0)} records")
            
            if result.get('warnings'):
                print(f"⚠️  Warnings:")
                for warning in result['warnings']:
                    print(f"   - {warning}")
            
            return True
        else:
            print(f"❌ ERROR: HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Message: {error_data.get('detail', {}).get('message', 'Unknown error')}")
                if error_data.get('detail', {}).get('details', {}).get('errors'):
                    print(f"   Errors:")
                    for error in error_data['detail']['details']['errors'][:5]:  # Show first 5 errors
                        print(f"      - {error}")
            except:
                print(f"   {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ ERROR: Cannot connect to backend at {API_BASE_URL}")
        print(f"   Make sure the backend server is running!")
        print(f"   Start it with: python -m uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False


def main():
    print("="*60)
    print("PMPML CSV Data Upload Script")
    print("="*60)
    print(f"Backend URL: {API_BASE_URL}")
    print(f"CSV Directory: {CSV_DATA_DIR}")
    print("="*60)
    
    # Check if backend is running
    try:
        response = requests.get(f"{API_BASE_URL.replace('/api', '')}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running")
        else:
            print("⚠️  Backend responded but health check failed")
    except:
        print("❌ ERROR: Backend is not running!")
        print("   Start it with: python -m uvicorn app.main:app --reload")
        return
    
    # Upload all files
    success_count = 0
    fail_count = 0
    
    for data_type, filename in FILES_TO_UPLOAD:
        file_path = os.path.join(CSV_DATA_DIR, filename)
        if upload_csv(data_type, file_path):
            success_count += 1
        else:
            fail_count += 1
            print(f"\n⚠️  Continuing with remaining files...")
    
    # Summary
    print(f"\n{'='*60}")
    print("UPLOAD SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successful: {success_count}/{len(FILES_TO_UPLOAD)}")
    print(f"❌ Failed: {fail_count}/{len(FILES_TO_UPLOAD)}")
    print(f"{'='*60}")
    
    if success_count == len(FILES_TO_UPLOAD):
        print("\n🎉 All files uploaded successfully!")
        print("\n📱 Driver App Login:")
        print("   All drivers can now login with password: test123")
        print("   Example: driver_id from CSV + password 'test123'")
        print("\n🚀 You can now:")
        print("1. Test driver app login with any driver_id + password 'test123'")
        print("2. Go to the frontend optimization page")
        print("3. Select a depot from the dropdown")
        print("4. Run optimization")
    elif success_count > 0:
        print("\n⚠️  Some files uploaded successfully, but some failed.")
        print("   Check the errors above and try uploading the failed files again.")
    else:
        print("\n❌ No files were uploaded successfully.")
        print("   Check that the backend is running and the CSV files are valid.")


if __name__ == "__main__":
    main()
