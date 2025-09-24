#!/usr/bin/env python3
"""Check actual structure of SAM.gov responses"""

import requests
import json

url = "https://sam.gov/api/prod/sgs/v1/search/"
params = {
    'index': 'opp',
    'q': 'DARPA',
    'page': 0,
    'sort': '-modifiedDate',
    'size': 2
}

response = requests.get(url, params=params, timeout=10)
data = response.json()

if '_embedded' in data and 'results' in data['_embedded']:
    print("SAM.gov Result Structure:\n")

    for i, item in enumerate(data['_embedded']['results'][:2], 1):
        print(f"Item {i} keys: {list(item.keys())}\n")
        print(f"Title: {item.get('title', 'N/A')[:60]}")

        # Print all fields
        for key, value in item.items():
            if key != 'title':
                if isinstance(value, str):
                    print(f"{key}: {value[:100] if len(value) > 100 else value}")
                elif isinstance(value, (dict, list)):
                    print(f"{key}: {type(value).__name__} with {len(value)} items")
                else:
                    print(f"{key}: {value}")
        print("\n" + "-" * 40 + "\n")