import argparse
import atexit
from bs4 import BeautifulSoup
import requests
import sqlite3
from Include.ThreadPool import ThreadPool
import urllib3
from urllib import parse
import validators

# Ignore SSL warnings, just need to know if page returns result
requests.urllib3.disable_warnings(requests.urllib3.exceptions.InsecureRequestWarning)

pool = ThreadPool(4)
base = ""
headers = ""


def main():
    global base, headers

    argParser = argparse.ArgumentParser(description="%(prog)s is a general broken link checker. Returns a list of broken URLs, their parent URL, and number of instances on the parent page.")
    argParser.add_argument("url", help="The base URL that you want to check")
    argParser.add_argument("--depth", "-d", type=int, default=1, help="Maximum degrees of separation of pages to crawl. 0 for unlimited depth")
    argParser.add_argument("--user-agent", "-u", default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36 link_checker/0.9", help="Alternative User-Agent to use with requests.get() headers")
    argParser.add_argument("--base", "-b", help="Overrides base domain for crawling. By default, only the subdomain provided by URL is crawled. By setting Base, you can cover multiple subdomains. Usage: example.com will search forums.example.com, www.example.com, and example.com")
    argParser.add_argument("--delay", "-t", type=int, default=0, help="Delay (in seconds) between consecutive website calls. Enabling a delay will slow down the process, but will help to ensure that you do not negatively impact target servers.")
    argParser.add_argument("--reset", "-r", type=bool, default=False, help="Resets local links database, restarting crawl. Default mode continues where previous crawl completed.")
    args = argParser.parse_args()

    headers = {
        "User-Agent": args.user_agent
    }
    
    if validate_url(args.url):
        base = args.base if args.base is not None else parse.urlsplit(args.url).hostname
    
        initialize_db()

        add_url(args.url)

        currentDepth = 0
        while args.depth == 0 or currentDepth < args.depth:
            print("Page depth: %d" % (currentDepth))
            # get unprocessed URLs
            urls = get_urls()

            if len(urls) == 0:
                break
            
            pool.map(process_url, urls)
            pool.wait_completion()
            currentDepth += 1
        else:
            print("Finishing up")
            urls = get_urls()
            pool.map(process_url_status, urls)
            pool.wait_completion()
        
        # Export report
        report = get_error_urls()
        if report is not None:
            with open("report.log", "w") as f:
                print(report, file=f)
    else:
        print("Invalid URL paremeter")

def add_url(url):
    urlId = 0
    db = get_db()
    cursor = db.cursor()

    try:
        link = parse.urldefrag(url)
        cursor.execute('SELECT url_id FROM url WHERE url=?', [link])
        result = cursor.fetchone()
        
        if result is None:
            cursor.execute('INSERT INTO url (url) VALUES (?);', [link])
            db.commit()
            urlId = cursor.lastrowid
        else:
            urlId = result[0]
    except sqlite3.IntegrityError:
        # value already exists, skip
        pass
    except sqlite3.Error as e:
        print("Database error: %s" % e)
    finally:
        db.close()

    return urlId

def initialize_db():
    db = get_db()
    # Create url table if not exists
    cursor = db.cursor()
    cursor.execute(''' CREATE TABLE IF NOT EXISTS url (
        url_id INTEGER PRIMARY KEY, 
        url TEXT NOT NULL, 
        status TEXT); ''')
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS urls ON url(url);')
    db.commit()

    # Create links table if not exists
    cursor.execute(''' CREATE TABLE IF NOT EXISTS links (
        parent_id INTEGER, 
        child_id INTEGER,
        url_count INTEGER,
        PRIMARY KEY(parent_id, child_id), 
        FOREIGN KEY (parent_id) REFERENCES url (url_id), 
        FOREIGN KEY (child_id) REFERENCES url (url_id)); ''')
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS mapping ON links(parent_id, child_id);')
    db.commit()
    db.close()

    return

def get_db():
    # TODO: use ':memory:' to use a virtual db file in production
    return sqlite3.connect('tmp_links.db')

def get_error_urls():
    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute(''' SELECT p.url AS 'parent', c.url AS 'child', c.status 
            FROM links 
            INNER JOIN url AS p ON parent_id = p.url_id 
            INNER JOIN url AS c ON child_id = c.url_id 
            WHERE c.status != 200
            ORDER BY child
            ''')
    except sqlite3.Error as e:
        print("Database error: %s" % e)
    
    result = cursor.fetchall()
    db.close()

    return result

def get_page(url):
    class MockResponse:
        def __init__(self, status_code = 0):
            self.status_code = status_code

    try:
        return requests.get(url, headers=headers, allow_redirects=True, verify=False)
    except:
        return MockResponse()

def get_urls():
    urls = []
    try:
        db = get_db()
        db.row_factory = lambda cursor, row: row[0]
        cursor = db.cursor()
        cursor.execute('SELECT url FROM url WHERE status IS NULL ORDER BY url;')
        urls = cursor.fetchall()
        db.close()
    except sqlite3.Error as e:
        print("Database error: %s" % e)

    return urls

def add_link(parent, child):
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT url_count FROM links WHERE parent_id=? AND child_id=?', [parent, child])
        result = cursor.fetchone()
        if result is None:
            cursor.execute('INSERT INTO links (parent_id, child_id, url_count) VALUES (?, ?, ?);', [parent, child, 1])
        else:
            cursor.execute('UPDATE links SET url_count=? WHERE parent_id=? AND child_id=?', [result[0] + 1, parent, child])
        db.commit()
        db.close()
        return True
    except sqlite3.IntegrityError:
        # value already exists, skip
        pass
    except sqlite3.Error as e:
        print("Database error: %s" %e)

    return False

def parse_content(base, content):
    soup = BeautifulSoup(content, "html.parser")
    
    links = []
    refs = soup.find_all("a", href=True)
    for a in refs:
        link = parse.urljoin(base, a['href'], False)
        print("Found: " + link)
        if validate_url(link):
            links.append(link)

    return links

def process_url(url):
    # Fetch page for each URL, save status_code to database
    page = get_page(url)
    update_url_status(url, page.status_code)

    print("Status: %d | Base: %s | Hostname: %s" % (page.status_code, base, parse.urlsplit(url).hostname))
    if page.status_code == 200 and "text/html" in page.headers['content-type'] and base in parse.urlsplit(url).hostname:
        links = parse_content(url, page.text)

        parentId = add_url(url) # already in Db, returns Id

        for link in links:
            childId = add_url(link)
            add_link(parentId, childId)

def process_url_status(url):
    # Fetch page for each URL, save status_code to database
    page = get_page(url)
    update_url_status(url, page.status_code)

def update_url_status(url, status):
    db = get_db()
    cursor = db.cursor()

    try:    
        cursor.execute('UPDATE url SET status=? WHERE url=?;', [status, url])
        if cursor.rowcount > 0:
            db.commit()
    except sqlite3.IntegrityError:
        # value already exists, skip
        pass
    except sqlite3.Error as e:
        print("Database error: %s" % e)
    
    db.close()   

def validate_url(url):
    try:
        # remove fragments from url and validate
        result = parse.urlsplit(url).geturl()
        return validators.url(result)
    except Exception as ex:
        print(str(ex))
        print("URL is malformed: %s" % url)
        return False

main()