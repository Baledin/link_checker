import link_checker

lc = link_checker
db = lc.get_db()

# Initialize if not already set
lc.initialize_db(db)

url_id = lc.add_url(db, "https://www.sos.wa.gov")

print("url_id: %d" % url_id)

for i in range(3):
    print(lc.add_link(db, url_id, url_id))

c = db.cursor()
c.execute(''' SELECT url_count FROM links WHERE parent_id=? AND child_id=? ''', [url_id, url_id])
result = c.fetchone()
assert result[0] == 3, "Incorrect url_count"

db.close()