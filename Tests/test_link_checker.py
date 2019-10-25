import link_checker
import requests

lc = link_checker

def main():
    # Note, tests are run in order by dependencies
    test_add_url()
    #test_add_link()
    #test_get_db()
    #test_get_error_urls()
    #test_get_header()
    #test_get_page()
    #test_get_urls()
    #test_initialize_db()
    #test_parse_content()
    #test_process_url()
    #test_process_url_status()
    #test_update_url_status()
    #test_validate_url()

def test_add_link():
    print("test_add_link starting")
    # Initialize if not already set
    conn = lc.get_connection(':memory:')
    lc.initialize_db(conn)

    url_id = lc.add_url("https://www.sos.wa.gov", conn)

    print("url_id: %d" % url_id)

    for _ in range(3):
        print(lc.add_link(url_id, url_id, conn))

    with conn.cursor() as c:
        c.execute(''' SELECT url_count FROM links WHERE parent_id=? AND child_id=? ''', [url_id, url_id])
        result = c.fetchone()

        conn.close()

    assert result[0] == 3, "Incorrect url_count: %s" % str(result)

    print("test_add_link complete")

def test_add_url():
    print("test_add_url starting")
    # Initialize if not already set
    conn = lc.get_connection(':memory:')
    lc.initialize_db(conn)

    url = "https://www.sos.wa.gov"

    for i in range(3):
        url_id = lc.add_url(url, conn)
        assert url_id == 1, "add_url test failed on pass " % i

    conn.close()
    print("test_add_url complete")

def test_get_db():
    #TODO
    assert True

def test_get_error_urls():
    #TODO
    assert True

def test_get_header():
    #TODO
    assert True

def test_get_page():
    #TODO
    assert True

def test_get_urls():
    #TODO
    assert True

def test_initialize_db():
    #TODO
    assert True

def test_parse_content():
    base = "sos.wa.gov"
    url = "https://www.sos.wa.gov/library"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
    }

    page = requests.get(url, headers=headers, allow_redirects=True)
    html = page.text

    print(lc.parse_content(url, html))

def test_process_url():
    #TODO
    assert True

def test_process_url_status():
    #TODO
    assert True

def test_update_url_status():
    #TODO
    assert True

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

if __name__ == "__main__":
    main()
