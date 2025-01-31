import requests
import json
import os
from dotenv import load_dotenv
load_dotenv()

def create_task(endpoint_url,payload):
    # URL for the API request
    
    # # Load payload from the JSON file
    # with open('data/payload.json', 'r') as json_file:
    #     payload = json.load(json_file)

    # Load the authorization token from the .env file
    auth_token = os.getenv("BearerToken")

    if not auth_token:
        print("Authorization token is missing in the .env file.")
        return None

    # Even though no file is being uploaded, include an empty file field to ensure proper boundary is created
    files = {
        'file_field': ('', '')  # empty field to trigger multipart boundary handling
    }

    # Headers including the Authorization token
    headers = {
        'Authorization': f'Bearer {auth_token}',
    }

    try:
        # Sending POST request
        response = requests.post(endpoint_url, headers=headers, data=payload, files=files)

        # Checking if the request was successful
        if response.status_code == 200:
            # Returning the response as a dictionary (parsed JSON)
            return response.json()
        else:
            print(f"Failed to create task: {response.status_code}", response.text)
            return None

    except Exception as e:
        print("An error occurred:", str(e))
        return None
