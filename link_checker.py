import argparse
from bs4 import BeautifulSoup
import logging
import os
import random
import requests
import sqlite3
import time
from urllib import parse
import validators

from Include.ThreadPool import ThreadPool

# Ignore SSL warnings, just need to know if page returns result
requests.urllib3.disable_warnings(requests.urllib3.exceptions.InsecureRequestWarning)

args = None
info_log = "link_checker.log"
report_log = "report.log"

def main():
    global args, info_log, report_log

    argParser = argparse.ArgumentParser(description="%(prog)s is a general broken link checker. Returns a list of broken URLs, their parent URL, and number of instances on the parent page.")
    argParser.add_argument("url", nargs="+", help="The URL(s) which will be the starting point for crawling to DEPTH levels deep.")
    argParser.add_argument("-d", "--depth", type=int, default=1, help="Maximum degrees of separation of pages to crawl. 0 for unlimited depth")
    argParser.add_argument("-u", "--user-agent", default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36 link_checker/0.9", help="Alternative User-Agent to use with requests.get() headers")
    argParser.add_argument("-b", "--base", help="Alternative hostnames for crawling. By default, only URLs matching the full hostname provided by URL is checked for additional links to crawl. By setting Base, you can add additional hostnames that will be considered for link checking.")
    argParser.add_argument("-t", "--threads", type=int, default=4, help="Sets the number of concurrent threads that can be processed at one time. Be aware that increasing thread count will increase the frequency of requests to the server.")
    argParser.add_argument("-r", "--reset", action="store_true", help="Resets logs and local links database, restarting crawl. Default (no flag) continues where previous crawl completed.")
    argParser.add_argument("--report-file", default=report_log, help="Filename of final report. Defaults to %s" % report_log)
    argParser.add_argument("-l", "--log-level", default="WARNING", choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"], help="Log level to report in %s." % info_log)
    argParser.add_argument("--log-file", default=info_log, help="Filename of informational log. Defaults to %s." % info_log)
    args = argParser.parse_args()

    info_log = args.log_file
    report_log = args.report_file

    logging.basicConfig(
        level=args.log_level,
        filename=info_log, 
        filemode= "w" if args.reset else "a",
        format="%(asctime)s\t%(levelname)s\t%(message)s")
    logging.info("***** link_checker started *****")
    logging.debug(args)

    check = True
    for url in args.url:
        check = check if validate_url(url) else False

    if check:
        # Initialize variables/db
        pool = ThreadPool(args.threads)
        
        conn = get_connection()
        initialize_db(conn, args.reset)

        args.base = set() if args.base is None else {args.base}

        for url in args.url:
            args.base.add(parse.urlsplit(url).hostname)
            add_url(conn, url)

        try:
            currentDepth = 0
            while args.depth == 0 or currentDepth < args.depth:
                logging.info("Current page depth: %d" % (currentDepth))
                # get unprocessed URLs
                urls = get_urls(conn)
                pool.map(process_url, urls)
                pool.wait_completion()
                currentDepth += 1
            else:
                logging.info("Finishing up")
                urls = get_urls(conn)

                #TODO must pass connection
                pool.map(process_url_status, urls)
                pool.wait_completion()
            
            # Export report
            report = get_error_urls(conn)
            if report is not None:
                with open("report.log", "w") as f:
                    print(report, file=f)
        finally:
            conn.close()
    else:
        logging.error("Invalid URL paremeter provded.")

def add_link(conn, parent, child):
    cursor = conn.cursor()

    try:
        logging.info("Updating links table - parent_id: %d | child_id: %d" % (parent, child))
        cursor.execute('INSERT INTO links (parent_id, child_id, url_count) VALUES (?, ?, ?);', [parent, child, 1])
        return True
    except sqlite3.IntegrityError:
        logging.info("Item already exists, updating record.")
        cursor.execute('UPDATE links SET url_count=url_count+1 WHERE parent_id=? AND child_id=?', [parent, child])
        return True
    except sqlite3.Error as e:
        logging.debug("Database error: %s" % e)
        logging.critical("Database error - ensure database is writable.")
    finally:
        conn.commit()

    return False

def add_url(conn, url):
    conn = get_connection() if conn is None else conn
    cursor = conn.cursor()
    urlId = 0

    link = parse.urldefrag(url).url
    
    try:
        logging.info("Adding URL '%s' to database." % link)
        cursor.execute('INSERT INTO url (url) VALUES (?);', [link])
        conn.commit()
        urlId = cursor.lastrowid
    except sqlite3.IntegrityError as e:
        logging.warning("URL '%s' already found in database." % link)
        cursor.execute('SELECT url_id FROM url WHERE url=?', [link])
        result = cursor.fetchone()
        urlId = result[0]
        pass
    except sqlite3.Error as e:
        logging.debug("Database error: %s" % e)
        logging.critical("Database error - ensure database is writable.")

    return urlId

def get_connection(db_name = 'tmp_links.db'):
    logging.info("Getting database connection: %s" % db_name)
    return sqlite3.connect(db_name)

def get_error_urls(conn):
    cursor = conn.cursor()

    try:
        cursor.execute(''' SELECT p.url AS 'parent', c.url AS 'child', c.status 
            FROM links 
            INNER JOIN url AS p ON parent_id = p.url_id 
            INNER JOIN url AS c ON child_id = c.url_id 
            WHERE c.status != 200
            ORDER BY child
            ''')
    except sqlite3.Error as e:
        logging.error("Database error: %s" % e)
    
    result = cursor.fetchall()

    return result

def get_header(url):
    headers = {
        "User-Agent": args.user_agent
    }

    try:
        return requests.head(url, headers=headers, allow_redirects=True, verify=False)
    except:
        return None

def get_page(url):
    headers = {
        "User-Agent": args.user_agent
    }

    try:
        return requests.get(url, headers=headers, allow_redirects=True, verify=False)
    except:
        return None

def get_urls(conn):
    urls = []
    try:
        conn.row_factory = lambda cursor, row: row[0]
        cursor = conn.cursor()
        cursor.execute('SELECT url FROM url WHERE status IS NULL ORDER BY url;')
        urls = cursor.fetchall()
    except sqlite3.Error as e:
        logging.error("Database error: %s" % e)

    return urls

def initialize_db(conn, reset = False):
    try:
        # Create url table if not exists
        cursor = conn.cursor()

        if reset:
            logging.warning("Resetting database tables")
            cursor.executescript('DROP TABLE IF EXISTS links; DROP TABLE IF EXISTS url;')
        
        logging.info("Initializing database tables")
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS url (url_id INTEGER PRIMARY KEY, url TEXT NOT NULL, status TEXT, notes TEXT);
            CREATE TABLE IF NOT EXISTS links (parent_id INTEGER, child_id INTEGER, url_count INTEGER, PRIMARY KEY(parent_id, child_id), FOREIGN KEY (parent_id) REFERENCES url (url_id), FOREIGN KEY (child_id) REFERENCES url (url_id));
            CREATE UNIQUE INDEX IF NOT EXISTS urls ON url(url);
            CREATE UNIQUE INDEX IF NOT EXISTS mapping ON links(parent_id, child_id);
            ''')
        conn.commit()
    except sqlite3.Error as e:
        logging.error("Database error: %s" % e)
        return False
    
    return True

def parse_content(base, content):
    soup = BeautifulSoup(content, "html.parser")
    
    links = []
    refs = soup.find_all("a", href=True)
    for a in refs:
        link = parse.urljoin(base, a['href'], False)
        logging.info("Found: " + link)
        if validate_url(link):
            links.append(link)

    return links

def process_url(url, get_content = True, conn = None):
    conn = get_connection() if conn is None else conn

    # Fetch head or head + contents for each URL, save status_code to database
    if parse.urlsplit(url).hostname in args.base:
        page = get_page(url)
        status = 0 if page is None else page.status_code
        
        update_url_status(url, status)

        if (get_content 
            and status == 200 and 
            "text/html" in page.headers['content-type']):

            links = parse_content(url, page.text)

            parentId = add_url(conn, url) # Inserts URL if necessary, returns Id

            for link in links:
                childId = add_url(conn, link)
                add_link(conn, parentId, childId)
    else:
        page = get_header(url)
        status = 0 if page is None else page.status_code

        update_url_status(url, status)
    
    if page is not None:
        time.sleep(page.elapsed.total_seconds() * random.randint(1, 5))
    conn.close()

def process_url_status(url):
    # Wrapper for process_url, setting parse_content to false
    process_url(url, False)

def update_url_status(url, status, conn = None):
    conn = get_connection() if conn is None else conn
    cursor = conn.cursor()

    try:    
        cursor.execute('UPDATE url SET status=? WHERE url=?;', [status, url])
        if cursor.rowcount > 0:
            conn.commit()
    except sqlite3.IntegrityError:
        # value already exists, skip
        pass
    except sqlite3.Error as e:
        logging.error("Database error: %s" % e)
    
    conn.close()   

def validate_url(url):
    logging.info("Validating URL: %s" % str(url))
    try:
        # remove fragments from url and validate
        result = validators.url(parse.urlsplit(url).geturl())
        if result:
            logging.info("URL is valid: %s" % url)
            return True
        else:
            logging.warning("URL is malformed: %s" % url)
            logging.debug(result)
            return False
    except Exception as ex:
        logging.debug(ex)
        return False

if __name__ == "__main__":
    main()
