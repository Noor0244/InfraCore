import urllib.request
import sys

def check(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            code = r.getcode()
            content = r.read(1000).decode('utf-8', 'ignore').replace('\n',' ')
            print(f"{url} -> {code}")
            print(content[:300])
            print('----')
    except Exception as e:
        print(f"{url} -> ERROR: {e}")
        print('----')

if __name__ == '__main__':
    base = 'http://127.0.0.1:8001'
    paths = ['/login','/projects','/projects/manage','/projects/new','/admin/users','/projects/1','/projects/1/edit']
    for p in paths:
        check(base + p)
