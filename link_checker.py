import sqlite3
import ThreadPool
import ThreadWorker

def db_connect():
    db = sqlite3.connect('tmp_links.db')
    return db

def initialize_db(db):
    # Check if url table exists
    cursor = db.cursor()
    cursor.execute(''' SELECT COUNT(name) FROM sqlite_master WHERE type='table' AND name='url' ''')
    if cursor.fetchone()[0]==0:
        # table does not exist
        print("Table url does not exist, creating")
        cursor.execute('''CREATE TABLE url (url_id INTEGER PRIMARY KEY, url VARCHAR(255) NOT NULL, status VARCHAR(50) NOT NULL)''')
        db.commit()
    else:
        print("Table url exists")

    # Check if links table exists
    cursor = db.cursor()
    cursor.execute(''' SELECT COUNT(name) FROM sqlite_master WHERE type='table' AND name='links' ''')
    if cursor.fetchone()[0]==0:
        # table does not exist
        print("Table links does not exist, creating")
        cursor.execute('''CREATE TABLE links (link_id INTEGER PRIMARY KEY, parent_id INTEGER, child_id INTEGER, FOREIGN KEY (parent_id) REFERENCES url (url_id), FOREIGN KEY (child_id) REFERENCES url(url_id))''')
        db.commit()
    else:
        print("Table links exists")

    return

db = db_connect()
initialize_db(db)
db.close()
