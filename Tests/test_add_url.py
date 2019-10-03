import link_checker

lc = link_checker
db = lc.get_db()

# Initialize if not already set
lc.initialize_db(db)

for i in range(3):
    print(lc.add_url(db, "https://www.sos.wa.gov"))

db.close()