import link_checker

db = link_checker.getDb()

# Initialize if not already set
link_checker.initialize_db(db)

for i in range(3):
    print(link_checker.add_url(db, "https://www.sos.wa.gov"))

db.close()