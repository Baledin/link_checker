import argparse
import atexit
from bs4 import BeautifulSoup
import requests
import sqlite3
from Include.ThreadPool import ThreadPool
from urllib import parse
import validators

pool = ThreadPool(4)

def main():
    argParser = argparse.ArgumentParser()
    argParser.add_argument("url", help="The base URL that you want to check")
    argParser.add_argument("--depth", "-d", help="Maximum degrees of separation of pages to crawl. 0 for unlimited depth", type=int, default=1)
    argParser.add_argument("--user-agent", "-u", help="Alternative User-Agent to use with requests.get() headers", default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36")
    args = argParser.parse_args()

    headers = {
        "User-Agent": args.user_agent
    }

    initialize_db(get_db())

def get_db():
    return sqlite3.connect('tmp_links.db')

def initialize_db(db):
    # Create url table if not exists
    cursor = db.cursor()
    cursor.execute(''' CREATE TABLE IF NOT EXISTS url (
        url_id INTEGER PRIMARY KEY, 
        url TEXT NOT NULL, 
        status TEXT); ''')
    cursor.execute(''' CREATE UNIQUE INDEX IF NOT EXISTS urls ON url(url); ''')
    db.commit()

    # Create links table if not exists
    cursor.execute(''' CREATE TABLE IF NOT EXISTS links (
        parent_id INTEGER, 
        child_id INTEGER,
        url_count INTEGER,
        PRIMARY KEY(parent_id, child_id), 
        FOREIGN KEY (parent_id) REFERENCES url (url_id), 
        FOREIGN KEY (child_id) REFERENCES url (url_id)); ''')
    cursor.execute(''' CREATE UNIQUE INDEX IF NOT EXISTS mapping ON links(parent_id, child_id); ''')
    db.commit()

    return

def validate_url(url):
    try:
        # remove fragments from url and validate
        result = parse.urlsplit(url).geturl()
        if validators.url(result):
            return result
        else:
            return None
    except Exception as ex:
        print(str(ex))
        print("URL is malformed: %s" % url)
        return None

def get_anchor_links(base, content):
    soup = BeautifulSoup(content, "html.parser")
    
    links = []
    refs = soup.find_all("a", href=True)
    for a in refs:
        link = parse.urljoin(base, a['href'])
        links.append(link)

    return links

def add_url(db, url):
    try:
        cursor = db.cursor()
        cursor.execute(''' SELECT url_id FROM url WHERE url=? ''', [url])
        result = cursor.fetchone()
        print(result)
        if result is None:
            cursor.execute(''' INSERT INTO url (url) VALUES (?); ''', [url])
            db.commit()
            return cursor.lastrowid
        else:
            return result[0]
    except sqlite3.IntegrityError:
        # value already exists, skip
        pass
    except sqlite3.Error as e:
        print("Database error: %s" % e)

    return 0

def add_link(db, parent, child):
    try:
        cursor = db.cursor()
        cursor.execute(''' SELECT url_count FROM links WHERE parent_id=? AND child_id=? ''', [parent, child])
        result = cursor.fetchone()
        if result is None:
            cursor.execute(''' INSERT INTO links (parent_id, child_id, url_count) VALUES (?, ?, ?); ''', [parent, child, 1])
        else:
            cursor.execute(''' UPDATE links SET url_count=? WHERE parent_id=? AND child_id=? ''', [result[0] + 1, parent, child])
        db.commit()
        return True
    except sqlite3.IntegrityError:
        # value already exists, skip
        pass
    except sqlite3.Error as e:
        print("Database error: %s" %e)

    return False

main()
