import link_checker

db = link_checker.getDb()

# Initialize if not already set
link_checker.initialize_db(db)

url_id = link_checker.add_url(db, "https://www.sos.wa.gov")

print("url_id: %d" % url_id)

for i in range(3):
    print(link_checker.add_link(db, url_id, url_id))

db.close()