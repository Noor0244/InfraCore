import urllib.request
import urllib.parse
import http.cookiejar

base = 'http://127.0.0.1:8000'

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# init session
opener.open(base + '/login?next=/projects/new', timeout=10).read()

# login with admin/admin123
form = urllib.parse.urlencode({'username': 'admin', 'password': 'admin123', 'next': '/projects/new'}).encode('utf-8')
req = urllib.request.Request(base + '/login', data=form, method='POST')
req.add_header('Content-Type', 'application/x-www-form-urlencoded')
resp = opener.open(req, timeout=10)
print('POST /login ->', getattr(resp, 'status', None), 'final:', resp.geturl())

html = opener.open(base + '/projects/new', timeout=10).read().decode('utf-8', 'ignore')
print('GET /projects/new bytes:', len(html))
print('has project_type select:', 'id="project_type"' in html)
print('has Create New Project:', 'Create New Project' in html)
