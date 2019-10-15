import link_checker
import requests

lc = link_checker

def main():
    test_add_link()
    test_add_url()
    test_get_anchor_links()
    test_validate_url()

def test_add_link():
    # Initialize if not already set
    lc.initialize_db()

    url_id = lc.add_url("https://www.sos.wa.gov")

    print("url_id: %d" % url_id)

    for i in range(3):
        print(lc.add_link(url_id, url_id))

    db = lc.get_db()
    c = db.cursor()
    c.execute(''' SELECT url_count FROM links WHERE parent_id=? AND child_id=? ''', [url_id, url_id])
    result = c.fetchone()
    assert result[0] == 3, "Incorrect url_count"

    db.close()

def test_add_url():
    # Initialize if not already set
    lc.initialize_db()

    for i in range(3):
        print(lc.add_url("https://www.sos.wa.gov"))

def test_get_anchor_links():
    base = "sos.wa.gov"
    url = "https://www.sos.wa.gov/library"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
    }

    page = requests.get(url, headers=headers, allow_redirects=True)
    html = page.text

    print(lc.parse_content(url, html))

def test_validate_url():
    valid_urls = (
        "http://google.com", 
        "http://localhost:8080", 
        "http://google.com/?test",
        "http://sos.wa.gov/library/libraries/default.aspx",
        "https://sos.wa.gov/library#contact",
        "https://sos.wa.gov/library/search?testquery=5&testanswer=5"
        )

    invalid_urls = (
        "//fredhutchcenter.com", 
        3,
        "notanaddress", 
        "http://localhost:[903]"
        )

    for url in valid_urls:
        assert link_checker.validate_url(url) != None, "%s is not valid" % str(url)

    for url in invalid_urls:
        assert link_checker.validate_url(url) == None, "%s is not valid" % str(url)

    print("validate_url passes")


main()