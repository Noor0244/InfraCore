import requests
import re
from datetime import date, timedelta

BASE = 'http://127.0.0.1:8001'

s = requests.Session()
print('Logging in as admin')
r = s.post(BASE + '/login', data={'username': 'admin', 'password': 'admin123'}, allow_redirects=True)
print('Login status:', r.status_code, '->', r.url)

# Create project
start = date.today()
end = start + timedelta(days=30)
create_data = {
    'name': 'Smoke Test Project',
    'road_type': 'State Highway',
    'lanes': '2',
    'road_width': '7.5',
    'road_length_km': '1.2',
    'country': 'India',
    'city': 'TestCity',
    'planned_start_date': start.isoformat(),
    'planned_end_date': end.isoformat(),
    'project_type': 'Road'
}
print('Creating project...')
r = s.post(BASE + '/projects/create', data=create_data, allow_redirects=True, timeout=10)
print('Create POST ->', r.status_code, 'final URL:', r.url)
match = re.search(r'/projects/(\d+)', r.url)
if not match:
    print('Failed to determine project id from redirect URL')
    print(r.text[:400])
    raise SystemExit(1)
project_id = int(match.group(1))
print('Created project id:', project_id)

# Update project
update_data = create_data.copy()
update_data['name'] = 'Smoke Test Project (Updated)'
print('Updating project...')
r = s.post(f"{BASE}/projects/{project_id}/update", data=update_data, allow_redirects=True, timeout=10)
print('Update ->', r.status_code, r.url)

# Archive project
print('Archiving project...')
r = s.post(f"{BASE}/projects/{project_id}/archive", allow_redirects=True, timeout=10)
print('Archive ->', r.status_code, r.url)

# Restore project (archive toggles)
print('Restoring project...')
r = s.post(f"{BASE}/projects/{project_id}/archive", allow_redirects=True, timeout=10)
print('Restore ->', r.status_code, r.url)

# Complete project
print('Completing project...')
r = s.post(f"{BASE}/projects/{project_id}/complete", allow_redirects=True, timeout=10)
print('Complete ->', r.status_code, r.url)

# Finally delete project
print('Deleting project...')
r = s.post(f"{BASE}/projects/{project_id}/delete", allow_redirects=True, timeout=10)
print('Delete ->', r.status_code, r.url)

# Verify project no longer accessible
print('Verifying deletion...')
r = s.get(f"{BASE}/projects/{project_id}", allow_redirects=True, timeout=10)
print('GET overview after delete ->', r.status_code, r.url)
print(r.text[:400].replace('\n',' '))

print('Flow complete')
