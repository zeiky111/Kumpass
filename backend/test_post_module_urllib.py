import json
import sys
from urllib import request, error

url = 'http://127.0.0.1:8000/api/instructor/modules/'
payload = {
    'actorEmail': 'irish@gmail.com',
    'title': 'POST test module from urllib',
    'description': 'testing',
    'year_level': '1',
}
data = json.dumps(payload).encode('utf-8')
req = request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
try:
    with request.urlopen(req, timeout=5) as resp:
        print('STATUS:', resp.getcode())
        print('BODY:', resp.read().decode('utf-8'))
except error.HTTPError as e:
    print('STATUS:', e.code)
    try:
        print('BODY:', e.read().decode('utf-8'))
    except Exception:
        print('BODY: <no body>')
except Exception as e:
    print('Error:', e)
    sys.exit(1)
