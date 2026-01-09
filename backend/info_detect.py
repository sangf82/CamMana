import requests
import os
import json

def test_api():
    # Configuration
    base_url = "https://thpttl12t1--truck-api-fastapi-app.modal.run"
    
    endpoints = {
        "ALPR": "/alpr",
        "Color Detection": "/detect_colors",
        "Wheel Counting": "/count_wheels"
    }

    images = [
        os.path.join("database", "captured_img", "xe-tai-cau-hino-3-chan-3-gio.jpg"),
        os.path.join("database", "captured_img", "cac-loai-xe-tai-cho-hang.jpg.webp"),
        os.path.join("database", "captured_img", "OIP.webp")
    ]

    for image_path in images:
        print("\n" + "="*80)
        print(f"TESTING IMAGE: {os.path.basename(image_path)}")
        print("="*80)

        # Check if image exists
        if not os.path.exists(image_path):
            print(f"Error: Image file not found at {image_path}")
            continue

        for name, path in endpoints.items():
            api_url = f"{base_url}{path}"
            print(f"\n--- Testing {name} ({api_url}) ---")
            
            try:
                with open(image_path, "rb") as f:
                    files = {"file": f}
                    response = requests.post(api_url, files=files)

                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(json.dumps(data, indent=4, ensure_ascii=False))
                    except json.JSONDecodeError:
                        print("Response is not JSON:")
                        print(response.text)
                else:
                    print(f"Failed. Status Code: {response.status_code}")
                    print("Response:", response.text)

            except requests.exceptions.RequestException as e:
                print(f"Request Error: {e}")
            except Exception as e:
                print(f"Unexpected Error: {e}")

if __name__ == "__main__":
    test_api()
