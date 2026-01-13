import requests, re
BASE='http://127.0.0.1:8001'
s=requests.Session()
# login
r=s.post(BASE+'/login', data={'username':'admin','password':'admin123'}, allow_redirects=True)
print('login', r.status_code)
# create road project with Flexible Pavement
create_data={
 'name':'Preset Road Project',
 'road_type':'Flexible Pavement (Bituminous)',
 'lanes':'2',
 'road_width':'7.5',
 'road_length_km':'2.5',
 'country':'India',
 'city':'PresetCity',
 'planned_start_date':'2026-01-01',
 'planned_end_date':'2026-06-01',
 'project_type':'Road',
 'road_construction_type':'Flexible Pavement (Bituminous)'
}
print('creating...')
r=s.post(BASE+'/projects/create', data=create_data, allow_redirects=True)
print('create status', r.status_code, 'url', r.url)
m=re.search(r'/projects/(\d+)', r.url)
if not m:
    print('failed get id')
    print(r.text[:1000])
    raise SystemExit(1)
pid=int(m.group(1))
print('project id', pid)
# fetch activity plan page
r=s.get(f'{BASE}/project-activity-plan/{pid}', allow_redirects=True)
print('plan page', r.status_code)
text=r.text
# crude check for activity names
names=['Clearing & Grubbing','Subgrade Preparation','Granular Sub-Base','Wet Mix Macadam','Prime Coat','Dense Bituminous Macadam','Bituminous Concrete','Road Marking & Finishing']
for n in names:
    found = n in text
    print(n, '->', found)
print('done')
