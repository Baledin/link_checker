import argparse
from io import StringIO
from lxml import etree
import requests
import sqlite3
import Include.ThreadPool
import Include.ThreadWorker
import urllib

def main():
    argParser = argparse.ArgumentParser()
    argParser.add_argument("--url", "-u", help="The base URL that you want to check")
    argParser.add_argument("--depth", "-d", help="Maximum degrees of separation of pages to crawl", type=int, default=1)
    argParser.add_argument("--headers", help="Alternative headers to use with requests.get()")
    args = argParser.parse_args()

    initialize_db(db_connect())

def db_connect():
    db = sqlite3.connect('tmp_links.db')
    return db

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

def check_url():
    return

def get_anchor_links(base, content):
    html_parser = etree.HTMLParser()
    tree = etree.parse(StringIO(content), parser=html_parser)
    
    refs = tree.xpath("//a")
    links = [urllib.parse.urljoin(base, link.get('href', '')) for link in refs]

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
