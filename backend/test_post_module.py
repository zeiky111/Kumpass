import json
import sys
import requests

url = 'http://127.0.0.1:8000/api/instructor/modules/'
payload = {
    'actorEmail': 'irish@gmail.com',
    'title': 'POST test module from script',
    'description': 'testing',
    'year_level': '1',
}
try:
    r = requests.post(url, json=payload, timeout=5)
    print('STATUS:', r.status_code)
    try:
        print('JSON:', r.json())
    except Exception:
        print('TEXT:', r.text)
except Exception as e:
    print('Error:', e)
    sys.exit(1)
