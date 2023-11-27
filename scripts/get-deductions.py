__requires__ = ['splinter[selenium3]', 'autocommand', 'keyring', 'requests']


import re
import getpass
import urllib.parse

import splinter
import autocommand
import keyring
import requests

url = 'https://itsdeductibleonline.intuit.com'
session = requests.session()


def get_login_form():
    username = getpass.getuser()
    return dict(
        Email=username,
        Password=keyring.get_password('https://link.intuit.com', username),
    )


def repair_js(base, href):
    if not href.startswith('javascript:'):
        return href
    target = re.search(r'\(\'(.*)\'\)', href).group(1)
    return urllib.parse.urljoin(base, target)


def download_data(browser, url):
    browser.visit(url)
    browser.find_by_text("View Summaries").click()
    links = browser.links.find_by_partial_href(".pdf")
    for link in links:
        download_pdf(repair_js(url, link['href']))


def copy_session_cookies(browser):
    for cookie in browser.driver.get_cookies():
        session.cookies.set(cookie['name'], cookie['value'])


def filename(resp):
    try:
        (name,) = re.findall('filename=(.+)', resp.headers['content-disposition'])
    except KeyError:
        name = resp.url.split('/')[-1]
    return name


def download_pdf(url):
    resp = session.get(url)
    resp.raise_for_status()
    with open(filename(resp), 'wb') as strm:
        strm.write(resp.content)


def run(browser):
    browser.visit(url)
    browser.find_by_text("Sign In").click()
    browser.fill_form(get_login_form())
    browser.find_by_name("SignIn").click()
    if browser.find_by_text("Let's make sure you're you"):
        browser.find_by_text("Text a code").click()
        input("respond to the code, then hit enter to continue")
    # load a page with older donations to find the URL format
    browser.find_by_text("2021 Donations").click()
    url_tmpl = browser.url.replace('2021', '{year}')
    copy_session_cookies(browser)
    for year in range(2005, 2023):
        download_data(browser, url_tmpl.format_map(locals()))


@autocommand.autocommand(__name__)
def main():
    preferences = {
        "browser.helperApps.neverAsk.saveToDisk": "application/pdf",
        "pdfjs.disabled": True,
    }
    with splinter.browser.Browser(profile_preferences=preferences) as browser:
        run(browser)
