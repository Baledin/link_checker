import link_checker
import requests
import urllib

url = "https://www.sos.wa.gov/library"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
}



with open("gov.wa.sos.www-library.html", "w") as f:
    page = requests.get(url, headers=headers, allow_redirects=True)
    html = page.content.decode("utf-8")

    print(link_checker.get_anchor_links(url, html), file=f)
    f.close
