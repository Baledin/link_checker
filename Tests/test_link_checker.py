from contextlib import closing
import link_checker
import logging
import random
import requests
import sqlite3

logging.basicConfig(
    level=logging.DEBUG,
    filename="link_checker_debug.log", 
    filemode="w", 
    format="%(asctime)s\t%(levelname)s\t%(message)s")
lc = link_checker
test_url = "https://www.sos.wa.gov/library/"

def main():
    lc.set_db("tests.db")

    # Database methods
    unit_initialize_db()
    unit_add_url_to_db()
    unit_add_link()
    unit_get_error_urls()
    unit_get_urls()
    unit_process_url()
    unit_process_url_no_parse()
    unit_update_url_status()

    # Utility methods
    unit_get_header()
    unit_get_page()
    unit_parse_content()
    unit_validate_url()

def unit_add_link():
    with closing(lc.get_connection()) as conn:
        logging.info("***** unit_add_link starting *****")

        if lc.initialize_db(True):
            logging.info("Database initialized.")
        else:
            logging.critical("Database failed to initialize.")
            exit()

        url_id = lc.add_url_to_db(test_url)

        r = random.randint(3, 10)
        logging.info("unit_add_link looping %d times." % r)
        for _ in range(r):
            lc.add_link(url_id, url_id)
        
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

def unit_add_url_to_db():
    logging.info("***** unit_add_url_to_db starting *****")
    
    # Initialize db
    lc.initialize_db(True)
    url = test_url
    url_id = lc.add_url_to_db(url)

    try:
        assert url_id > 0
        logging.info("unit_add_url_to_db passed - %s added to db." % url)
    except AssertionError:
        logging.info("unit_add_url_to_db failed - %s not found." % url)
    
    logging.info("***** unit_add_url_to_db complete *****")

def unit_get_error_urls():
    logging.info("***** unit_get_error_urls starting *****")
    lc.initialize_db(True)

    total_urls=9
    error_urls=[]

    # Initialize urls, url should match child from get_error_urls
    for i in range(1, total_urls):
        url = test_url + str(i)
        lc.add_url_to_db(url)
        r = random.randint(0, 1)
        status_code = 200
        if r:
            error_urls.append(url)
            status_code = 404
        lc.update_url_status(url, status_code, 0)
        lc.add_link(1, i)

    try:
        results = lc.get_error_urls()
        error_urls.sort()
        if len(results) == len(error_urls):
            for i in range(len(results)):
                assert error_urls[i] == results[i]['child']
        else:
            logging.critical("unit_get_error_urls failed: wrong number of rows returned. Expected %d, found %d." % (len(error_urls), len(results)))
    except AssertionError as ex:
        logging.critical("unit_get_error_urls failed: expected child %s | received %s" % (error_urls[i], results[i]['child']))
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

def unit_initialize_db():
    logging.info("***** unit_initialize_db starting *****")
    try:
        assert lc.initialize_db(True)
    except AssertionError as ex:
        logging.critical("Database initialization failed.")
        logging.error(str(ex))
        exit("unit_initiallize_db failed, check debug log.")
    
    try:
        with closing(lc.get_connection()) as conn:
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
        "3",
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
