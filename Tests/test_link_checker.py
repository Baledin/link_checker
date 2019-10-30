import link_checker
import logging
import random
import requests

logging.basicConfig(
    level=logging.DEBUG,
    filename="link_checker-debug.log", 
    filemode="w", 
    format="%(asctime)s\t%(levelname)s\t%(message)s")
lc = link_checker
test_url = "https://www.sos.wa.gov/library"

def main():
    unit_add_link()
    unit_add_url()
    unit_get_error_urls()
    unit_get_header()
    unit_get_page()
    unit_get_urls()
    unit_initialize_db()
    unit_parse_content()
    unit_process_url()
    unit_process_url_status()
    unit_update_url_status()
    unit_validate_url()

def unit_add_link():
    logging.info("***** unit_add_link starting *****")
    # Initialize if not already set
    conn = lc.get_connection(':memory:')
    lc.initialize_db(conn)

    url_id = lc.add_url(test_url, conn)

    r = random.randint(3, 10)
    logging.info("unit_add_link looping %d times." % r)
    for _ in range(r):
        lc.add_link(url_id, url_id, conn)

    c = conn.cursor()
    c.execute(''' SELECT url_count FROM links WHERE parent_id=? AND child_id=? ''', [url_id, url_id])
    result = c.fetchone()
    conn.close()

    # As add_link iterates counter, result should be equal to number of loops
    try:
        assert result[0] == r
        logging.info("unit_add_link passed - %d expected, %d found." % (r, result[0]))
    except AssertionError as e:
        logging.error("unit_add_link failed - %d expected, %d found." % (r, result[0]))
        logging.debug(e)

    logging.info("***** unit_add_link complete *****")

def unit_add_url():
    logging.info("***** unit_add_url starting *****")
    
    # Initialize db if not already set
    conn = lc.get_connection(':memory:')
    lc.initialize_db(conn)
    url = test_url

    url_id = lc.add_url(url, conn)

    try:
        assert url_id > 0
        logging.info("unit_add_url passed - %s added to db." % url)
    except AssertionError:
        logging.info("unit_add_url failed - %s not found." % url)

    conn.close()
    
    logging.info("***** unit_add_url complete *****")

def unit_get_error_urls():
    logging.info("***** unit_get_error_urls starting *****")
    assert True
    logging.info("***** unit_get_error_urls complete *****")

def unit_get_header():
    logging.info("***** unit_get_header starting *****")
    #TODO
    assert True
    logging.info("***** unit_get_header complete *****")

def unit_get_page():
    logging.info("***** unit_get_page starting *****")
    #TODO
    assert True
    logging.info("***** unit_get_page complete *****")

def unit_get_urls():
    logging.info("***** unit_get_urls starting *****")
    #TODO
    assert True
    logging.info("***** unit_get_urls complete *****")

def unit_initialize_db():
    logging.info("***** unit_initialize_db starting *****")
    #TODO
    assert True
    logging.info("***** unit_initialize_db complete *****")

def unit_parse_content():
    logging.info("***** unit_parse_content starting *****")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
    }
    #TODO
    assert True
    logging.info("***** unit_parse_content complete *****")

def unit_process_url():
    logging.info("***** unit_process_url starting *****")
    #TODO
    assert True
    logging.info("***** unit_process_url complete *****")

def unit_process_url_status():
    logging.info("***** unit_process_url_status starting *****")
    #TODO
    assert True
    logging.info("***** unit_process_url_status complete *****")

def unit_update_url_status():
    logging.info("***** unit_update_url_status starting *****")
    #TODO
    assert True
    logging.info("***** unit_update_url_status complete *****")

def unit_validate_url():
    logging.info("***** unit_validate_url starting *****")
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
        try:
            assert lc.validate_url(url)
        except AssertionError as ex:
            logging.debug(ex)

    for url in invalid_urls:
        try:
            assert lc.validate_url(url) == False
        except AssertionError as ex:
            logging.debug(ex)

    logging.info("***** unit_validate_url complete *****")

if __name__ == "__main__":
    main()
