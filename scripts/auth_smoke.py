import requests

BASE = 'http://127.0.0.1:8001'

paths = ['/dashboard','/projects','/projects/manage','/projects/new','/admin/users','/projects/1','/projects/1/edit']

s = requests.Session()
# login with seeded admin
r = s.post(BASE + '/login', data={'username': 'admin', 'password': 'admin123'}, allow_redirects=True)
print('LOGIN ->', r.status_code)
print(r.url)

for p in paths:
    try:
        r = s.get(BASE + p, timeout=5)
        print(f"{p} -> {r.status_code}")
        print(r.text[:200].replace('\n',' '))
    except Exception as e:
        print(f"{p} -> ERROR: {e}")
