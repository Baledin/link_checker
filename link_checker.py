import argparse
from bs4 import BeautifulSoup
from contextlib import closing
import logging
import os
import random
import requests
import sqlite3
import time
from urllib import parse
import validators
import webbrowser

from Include.ThreadPool import ThreadPool

# Ignores SSL warnings, just need to know if page returns result
requests.urllib3.disable_warnings(
    requests.urllib3.exceptions.InsecureRequestWarning)

args = None
db_name = "links.db"
info_log = "link_checker.log"
report_log = "report.html"


def main():
    global args, info_log, report_log

    argParser = argparse.ArgumentParser(description="%(prog)s is a general broken link checker. Returns a list of broken URLs, their parent URL, and number of instances on the parent page.")
    argParser.add_argument("url", nargs="+", help="The URL(s) which will be the starting point for crawling to DEPTH levels deep.")
    argParser.add_argument("-d", "--depth", type=int, default=1, help="Maximum degrees of separation of pages to crawl. 0 for unlimited depth, defaults to 1 level.")
    argParser.add_argument("-u", "--user-agent", default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36 link_checker/0.9", help="Alternative User-Agent to use with requests.get() headers")
    argParser.add_argument("-b", "--base", help="Alternative hostnames for crawling. By default, only URLs matching the full hostname provided by URL is checked for additional links to crawl. By setting Base, you can add additional hostnames that will be considered for link checking.")
    argParser.add_argument("-nq", "--no-query", action="store_true", help="Ignore the query portion of the url.")
    #TODO: Clarify this help
    argParser.add_argument("-ak", "--acceptable-keys", nargs="+", help="Acceptable query Keys for comparing URLs, any unspeccified keys will be ignored.")
    argParser.add_argument("-t", "--threads", type=int, default=2, help="Sets the number of concurrent threads that can be processed at one time. Be aware that increasing thread count will increase the frequency of requests to the server.")
    argParser.add_argument("-r", "--reset", action="store_true", help="Resets logs and local links database, restarting crawl. Default (no flag) continues where previous crawl completed.")
    argParser.add_argument("--report-file", default=report_log, help="Filename of final report. Defaults to %s" % report_log)
    argParser.add_argument("-l", "--log-level", default="INFO", choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"], help="Log level to report in %s." % info_log)
    argParser.add_argument("--log-file", default=info_log,help="Filename of informational log. Defaults to %s." % info_log)
    args = argParser.parse_args()

    info_log = args.log_file
    report_log = args.report_file

    logging.basicConfig(
        level=args.log_level,
        filename=info_log,
        filemode="w+" if args.reset else "a",
        format="%(asctime)s\t%(levelname)s\t%(message)s")
    logging.info("***** link_checker started *****")
    logging.debug(args)

    if not all(validate_url(url) for url in args.url):
        logging.error("Invalid URL paremeter provded.")
        exit("Please enter valid URL(s)")

    # Initialize variables/db
    pool = ThreadPool(args.threads)
    args.base = set() if args.base is None else {args.base}

    initialize_db(args.reset)

    # Process initial URLs
    for url in args.url:
        args.base.add(parse.urlsplit(url).hostname)
        pool.add_task(process_url, url, True)

    pool.wait_completion()

    currentDepth = 1
    while args.depth == 0 or currentDepth < args.depth:
        logging.info("Current page depth: %d" % currentDepth)
        # get unprocessed URLs
        urls = get_urls()

        if len(urls) == 0:
            logging.info("No URLs to check, exiting main loop.")
            break

        for url in urls:
            pool.add_task(process_url, url, True)
        pool.wait_completion()
        currentDepth += 1
    else:
        urls = get_urls()
        for url in urls:
            pool.add_task(process_url, url, False)
        pool.wait_completion()

    # Export report
    logging.info("Creating link report.")
    results = get_error_urls()
    with open(report_log, "w") as f:
        print("<html>", file=f)
        print("<head>", file=f)
        print("<style>", file=f)
        print("    h1 { font-size: 1.2em; }", file=f)
        print("    li { vertical-align: top; max-width: 80vw; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }", file=f)
        print(
            "    .status { display: inline-block; width: 30px; color: red; margin-right: 1em; text-align: right; }", file=f)
        print("</style>", file=f)
        print("</head>", file=f)
        print("<body>", file=f)
        heading = ""
        ignore_status = [401, 405, 500, 503]
        for result in results:
            if result['status'] in ignore_status:
                # Access forbidden, ignore
                continue

            if heading != result['parent']:
                if heading != "":
                    print("</ul>", file=f)
                print(
                    "<h1><a href='{url}' target='_blank'>{url}</a></h1>".format(url=result['parent']), file=f)
                print("<ul>", file=f)
                heading = result['parent']

            print("<li><span class='status'>{status}</span><a href='{url}' target='_blank'>{url}</a></li>".format(
                url=result['child'], status=result['status']), file=f)

        print("</ul>", file=f)  # Close final list
        print("</body>", file=f)
        print("</html>", file=f)
    webbrowser.open('file://' + os.path.realpath(report_log), new=2)


def add_link(parent, child):
    with closing(get_connection()) as conn:
        try:
            logging.info(
                "Updating links table - parent_id: %d | child_id: %d" % (parent, child))
            conn.execute('INSERT INTO links (parent_id, child_id, url_count) VALUES (?, ?, ?);', [
                         parent, child, 1])
        except sqlite3.IntegrityError:
            logging.info("Item already exists, updating record.")
            conn.execute(
                'UPDATE links SET url_count=url_count+1 WHERE parent_id=? AND child_id=?', [parent, child])
        except sqlite3.Error as e:
            logging.debug("Database error: %s" % e)
            logging.critical("Database error - ensure database is writable.")
            return False
        conn.commit()
    return True


def add_url_to_db(url):
    with closing(get_connection()) as conn:
        link = parse.urldefrag(url).url

        try:
            logging.info("Adding URL '%s' to database." % link)
            c = conn.execute('INSERT INTO url (url) VALUES (?);', [link])
            conn.commit()
            return c.lastrowid
        except sqlite3.IntegrityError as e:
            logging.warning("URL '%s' already found in database." % link)
            c = conn.execute('SELECT url_id FROM url WHERE url=?', [link])
            return c.fetchone()[0]
        except sqlite3.Error as e:
            logging.debug("Database error: %s" % e)
            logging.critical("Database error - ensure database is writable.")
            return None


def get_connection():
    logging.info("Getting database connection: %s" % db_name)
    return sqlite3.connect(db_name)


def get_error_urls():
    try:
        logging.info("Fetching URLs with error status.")
        with closing(get_connection()) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(''' 
                SELECT p.url AS 'parent', c.url AS 'child', url_count AS 'count', c.status 
                FROM links 
                INNER JOIN url AS p ON parent_id = p.url_id 
                INNER JOIN url AS c ON child_id = c.url_id 
                WHERE c.status > 403 OR c.status = 0
                ORDER BY parent, c.status, child;
                ''')
            return cursor.fetchall()
    except sqlite3.Error as e:
        logging.error("Database error: %s" % e)
        exit("Database error: %s" % e)


def get_page(url):
    headers = {"User-Agent": args.user_agent}

    try:
        return requests.get(url, headers=headers, allow_redirects=True, verify=False, stream=True)
    except:
        return None


def get_urls():
    with closing(get_connection()) as conn:
        try:
            conn.row_factory = lambda cursor, row: row[0]
            cursor = conn.execute(
                'SELECT url FROM url WHERE status IS NULL ORDER BY url;')
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error("Database error: %s" % e)
            return None


def initialize_db(reset=False):
    with closing(get_connection()) as conn:
        try:
            if reset:
                logging.warning("Resetting database tables")
                conn.executescript(
                    'DROP TABLE IF EXISTS links; DROP TABLE IF EXISTS url;')
                conn.commit()

            # Create url table if not exists
            logging.info("Initializing database tables")
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS url (url_id INTEGER PRIMARY KEY, url TEXT NOT NULL, status INTEGER, parsed INTEGER, notes TEXT);
                CREATE TABLE IF NOT EXISTS links (parent_id INTEGER, child_id INTEGER, url_count INTEGER, PRIMARY KEY(parent_id, child_id), FOREIGN KEY (parent_id) REFERENCES url (url_id), FOREIGN KEY (child_id) REFERENCES url (url_id));
                CREATE UNIQUE INDEX IF NOT EXISTS urls ON url(url);
                CREATE UNIQUE INDEX IF NOT EXISTS mapping ON links(parent_id, child_id);
                ''')
            conn.commit()
        except sqlite3.Error as e:
            logging.error("Database error: %s" % e)
            exit("Database error, check that database is writable.")

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


def process_url(url, get_content=True):
    # Fetch head or head + contents for each URL, save status_code to database
    logging.info("Processing Url: %s. get_content is %s" %
                 (url, str(get_content)))

    # TODO: Find out why page is not getting updated in DB
    # Accept URL input and get page
    #page = get_page(url)
    with get_page(url) as page:

        # add url to db
        parentId = add_url_to_db(url)  # Inserts URL if necessary, returns Id

        # Handle pages which don't resolve
        if page is None:
            update_url_status(parentId, 0, False)
            return

        # get status code of url
        status = page.status_code

        # update status of current page
        update_url_status(parentId, status, get_content)

        # if page.history (??) then add each page and status code to db, add page.url (the final redirected url) to db
        if len(page.history) > 0:
            update_url_status(add_url_to_db(page.url), page.status_code, get_content)

        # if current url is in args.base, and get_content, and url status code is OK, finally page is of the appropriate type, then scrape page for new links
        # for each link, add to the url, returning child ID, add to links table
        if (parse.urlsplit(url).hostname in args.base
            and get_content
            and status == 200
                and "text/html" in page.headers['content-type']):
            links = parse_content(url, page.text)

            for link in links:
                childId = add_url_to_db(link)
                add_link(parentId, childId)

        time.sleep(page.elapsed.total_seconds() * random.randint(1, 5))


def set_db(filename):
    global db_name
    db_name = filename


def update_url_status(url_id, status, parsed):
    with closing(get_connection()) as conn:
        try:
            logging.info("Updating %d | status: %d | parsed: %d" %
                         (url_id, status, parsed))
            cursor = conn.execute('UPDATE url SET status=?, parsed=? WHERE url_id=?;', [
                                  status, parsed, url_id])
            if cursor.rowcount > 0:
                conn.commit()
                logging.info("Record updated.")
        except sqlite3.IntegrityError:
            logging.warning("Integrity error updating status.")
            pass
        except sqlite3.Error as e:
            logging.error("Database error: %s" % e)


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
