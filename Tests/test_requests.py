import requests

urls = ['http://localhost/','http://www.washingtonruralheritage.org/', 'https://libraryasleader.org/' ]
headers = { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36 link_checker/0.9'}

def get_page(url):
    class MockResponse:
        def __init__(self, status_code = 0):
            self.status_code = status_code

    try:
        return requests.get(url, headers=headers, allow_redirects=True, verify=False)
    except:
        return MockResponse()

for url in urls:
    page = get_page(url)
    print ("%s : %d" % (url, page.status_code))