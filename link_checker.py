#TODO change URL nargs to + to require at least one response
import argparse
from bs4 import BeautifulSoup
import random
import requests
import sqlite3
import time
from urllib import parse
import validators

from Include.ThreadPool import ThreadPool

# Ignore SSL warnings, just need to know if page returns result
requests.urllib3.disable_warnings(requests.urllib3.exceptions.InsecureRequestWarning)

pool = ThreadPool(4)
args = None


def main():
    global args

    argParser = argparse.ArgumentParser(description="%(prog)s is a general broken link checker. Returns a list of broken URLs, their parent URL, and number of instances on the parent page.")
    argParser.add_argument("url", nargs="*", help="The URL(s) to check for link errors.")
    argParser.add_argument("-d", "--depth", type=int, default=1, help="Maximum degrees of separation of pages to crawl. 0 for unlimited depth")
    argParser.add_argument("-u", "--user-agent", default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36 link_checker/0.9", help="Alternative User-Agent to use with requests.get() headers")
    argParser.add_argument("-b", "--base", help="Overrides base domain for crawling. By default, only the subdomain provided by URL is crawled. By setting Base, you can cover multiple subdomains. Usage: example.com will search forums.example.com, www.example.com, and example.com")
    argParser.add_argument("-t", "--delay", type=int, default=0, help="Delay (in seconds) between consecutive website calls. Enabling a delay will slow down the process, but will help to ensure that you do not negatively impact target servers.")
    argParser.add_argument("-r", "--reset", action="store_true", help="Resets local links database, restarting crawl. Default (no flag) continues where previous crawl completed.")
    args = argParser.parse_args()

    check = True

    for url in args.url:
        check = check if validate_url(url) else False

    if check:
        args.base = args.base if args.base is not None else parse.urlsplit(args.url).hostname
    
        initialize_db()

        for url in args.url:
            add_url(url)

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
        print("Invalid URL paremeter provded.")

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

def process_url(url, get_content = True):
    # Fetch head or head + contents for each URL, save status_code to database
    if args.base in parse.urlsplit(url).hostname:
        page = get_page(url)
        status = 0 if page is None else page.status_code
        
        update_url_status(url, status)

        print("Status: %d | Base: %s | Hostname: %s" % (status, args.base, parse.urlsplit(url).hostname))
        if (get_content 
            and status == 200 and 
            "text/html" in page.headers['content-type']):

            links = parse_content(url, page.text)

            parentId = add_url(url) # Inserts URL if necessary, returns Id

            for link in links:
                childId = add_url(link)
                add_link(parentId, childId)
    else:
        page = get_header(url)
        status = 0 if page is None else page.status_code

        update_url_status(url, status)
    
    time.sleep(page.elapsed.total_seconds() * random.randint(1, 5))

def process_url_status(url):
    # Wrapper for process_url, setting parse_content to false
    process_url(url, False)

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
