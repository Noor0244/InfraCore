import urllib.request
import urllib.parse
import http.cookiejar
import re

base = 'http://127.0.0.1:8000'

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1) fetch login page to init session cookie
opener.open(base + '/login?next=/projects/new', timeout=10).read()

# 2) login
form = urllib.parse.urlencode({'username': 'admin', 'password': 'admin123', 'next': '/projects/new'}).encode('utf-8')
req = urllib.request.Request(base + '/login', data=form, method='POST')
req.add_header('Content-Type', 'application/x-www-form-urlencoded')
resp = opener.open(req, timeout=10)
print('POST /login ->', getattr(resp, 'status', None), 'final:', resp.geturl())

# 3) load create-project page
html = opener.open(base + '/projects/new', timeout=10).read().decode('utf-8', 'ignore')
print('GET /projects/new bytes:', len(html))

m = re.search(r'<select[^>]*id="project_type"[^>]*>(.*?)</select>', html, re.S | re.I)
if not m:
    print('project_type select not found')
else:
    inner = m.group(1)
    opts = re.findall(r'<option\s+[^>]*value="([^"]*)"', inner, re.I)
    print('project_type option count:', len(opts))
    # Show distinct non-empty values
    values = [o for o in opts if o.strip()]
    print('non-empty count:', len(values))
    print('first 15:', values[:15])

print('contains Road option:', 'value="Road"' in html)
print('contains fallback loop marker (legacy_project_types):', 'legacy_project_types' in html)
