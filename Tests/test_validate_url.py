import link_checker

valid_urls = (
    "http://google.com", 
    "http://localhost:8080", 
    "http://google.com/?test",
    "http://sos.wa.gov/library/libraries/default.aspx",
    "https://sos.wa.gov/library#contact",
    "https://sos.wa.gov/library/search?testquery=5&testanswer=5"
    )

invalid_urls = (
    "//fredhutchcenter.com", 
    3,
    "notanaddress", 
    "http://localhost:[903]"
    )

for url in valid_urls:
    assert link_checker.validate_url(url) != None, "%s is not valid" % str(url)

for url in invalid_urls:
    assert link_checker.validate_url(url) == None, "%s is not valid" % str(url)

print("validate_url passes")