from contextlib import closing
import link_checker
import logging
import random
import requests
import sqlite3

logging.basicConfig(
    level=logging.DEBUG,
    filename="link_checker-debug.log", 
    filemode="w", 
    format="%(asctime)s\t%(levelname)s\t%(message)s")
lc = link_checker
test_url = "https://www.sos.wa.gov/library/"

def main():
    lc.set_db("tests.db")
    with closing(lc.get_connection()) as conn:
        # Database methods
        unit_initialize_db(conn)
        unit_add_url(conn)
        unit_add_link(conn)
        unit_get_error_urls(conn)
        unit_get_urls()
        unit_process_url()
        unit_process_url_no_parse()
        unit_update_url_status()

        # Utility methods
        unit_get_header()
        unit_get_page()
        unit_parse_content()
        unit_validate_url()

def unit_add_link(conn):
    logging.info("***** unit_add_link starting *****")

    if lc.initialize_db(conn, True):
        logging.info("Database initialized.")
    else:
        logging.critical("Database failed to initialize.")
        exit()

    url_id = lc.add_url(conn, test_url)

    r = random.randint(3, 10)
    logging.info("unit_add_link looping %d times." % r)
    for _ in range(r):
        lc.add_link(conn, url_id, url_id)
    
    c = conn.execute(''' SELECT url_count FROM links WHERE parent_id=? AND child_id=? ''', [url_id, url_id])
    result = c.fetchone()

    # As add_link iterates counter, result should be equal to number of loops
    try:
        assert result[0] == r
        logging.info("unit_add_link passed - %d expected, %d found." % (r, result[0]))
    except AssertionError as e:
        logging.error("unit_add_link failed - %d expected, %d found." % (r, result[0]))
        logging.debug(e)

    logging.info("***** unit_add_link complete *****")

def unit_add_url(conn):
    logging.info("***** unit_add_url starting *****")
    
    # Initialize db
    lc.initialize_db(conn, True)
    url = test_url
    url_id = lc.add_url(conn, url)

    try:
        assert url_id > 0
        logging.info("unit_add_url passed - %s added to db." % url)
    except AssertionError:
        logging.info("unit_add_url failed - %s not found." % url)
    
    logging.info("***** unit_add_url complete *****")

def unit_get_error_urls(conn):
    logging.info("***** unit_get_error_urls starting *****")
    lc.initialize_db(conn, True)

    total_urls=9
    error_urls=0

    # Initialize urls
    for i in range(1, total_urls):
        url = test_url + str(i)
        lc.add_url(conn, url)
        r = random.randint(0, 1)
        error_urls = error_urls + r
        status_code = 404 if r else 200
        lc.update_url_status(conn, url, status_code, 0)
        lc.add_link(conn, 1, i)

    result = lc.get_error_urls(conn)
    try:
        for row in result:
            print(row)
        assert len(result) == error_urls
    except AssertionError as ex:
        logging.critical("unit_get_error_urls failed: %d | %s" % (error_urls, str(result)))
        logging.debug(ex)

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

def unit_initialize_db(conn):
    logging.info("***** unit_initialize_db starting *****")
    try:
        assert lc.initialize_db(conn, True)
    except AssertionError as ex:
        logging.critical("Database initialization failed.")
        logging.error(str(ex))
        exit("unit_initiallize_db failed, check debug log.")

    try:
        tables = ('links', 'url') # list must be in alpha order
        result = conn.execute('''
            SELECT tbl_name 
            FROM "main".sqlite_master 
            WHERE type='table'
            ORDER BY tbl_name;
            ''').fetchall()
        for i in range(len(tables)):
            assert tables[i] == result[i][0], logging.debug("Comparing %s to %s." % (tables[i], result[i][0]))
    except Exception as ex:
        logging.error(str(ex))
        exit("Table selection failed.")
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

def unit_process_url_no_parse():
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
