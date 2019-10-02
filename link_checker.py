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
        PRIMARY KEY(parent_id, child_id), 
        FOREIGN KEY (parent_id) REFERENCES url (url_id), 
        FOREIGN KEY (child_id) REFERENCES url (url_id)); ''')
    cursor.execute(''' CREATE UNIQUE INDEX IF NOT EXISTS mapping ON links(parent_id, child_id); ''')
    db.commit()
    db.close()

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
    cursor = db.cursor()
    cursor.execute(''' INSERT INTO url (url) VALUES (?); ''', [url])
    print(cursor.lastrowid)
    db.commit()
    db.close()

def add_link(db, parent, child):
    cursor = db.cursor()
    cursor.execute(''' INSERT INTO links (parent_id, child_id) VALUES (?, ?); ''', [parent, child])
    db.commit()
    db.close()

main()