#!  /usr/local/bin/python

"""Get Image Links.

Usage:
  get-image-links.py [--dir=<dir>] [--serial] <url>
  get-image-links.py [--just-show-links] <url>

Options:
  -h --help             Show this screen.
  --dir=<dir>           Set output directory explicitly.
  -s --serial           Serialise image downloading.
  -j --just-show-links  Show image links from index page
"""
from docopt import docopt

from bs4 import BeautifulSoup, SoupStrainer
from requests import Response
import grequests
import sys
import signal
from selenium import webdriver
from urlparse import urljoin, urlparse
from urllib import urlretrieve
from os import mkdir, path

def exception_handler(request, exception):
    print "Request {} failed".format(request.url)

def get_image_links_from(base_url):
    driver = webdriver.PhantomJS(service_args=['--load-images=no'])
    print "Fetching base page {}".format(base_url)
    driver.get(base_url)
    html = driver.page_source
    b = BeautifulSoup(html, 'html.parser')
    try:
        driver.service.process.send_signal(signal.SIGTERM)
        driver.quit()
    except: 
        pass

    for link in b.find_all('a'):
        if link.has_attr('href') and "full" in link['href']:
            print(urljoin(base_url, link['href']))

def download_images_from(base_url, **kwargs):
    parallel = kwargs.get("parallel", True)

    (default_dir, _) = path.splitext(path.basename(urlparse(base_url).path))
    dest_dir = kwargs.get("dir") or default_dir
    if path.exists(dest_dir) and  not path.isdir(dest_dir):
        print "{} is an existing file - it needs to be a directory".format(dest_dir)
        exit(1)

    driver = webdriver.PhantomJS(service_args=['--load-images=no'])
    print "Fetching base page {}".format(base_url)
    driver.get(base_url)
    html = driver.page_source
    b = BeautifulSoup(html, 'html.parser')
    try:
        driver.service.process.send_signal(signal.SIGTERM)
        driver.quit()
    except: 
        pass

    image_urls = []

    for image in b.find_all('img'):
        if "large" in image['src']:
            image_urls.append(urljoin(base_url, image['src']))

    if not path.exists(dest_dir):
        mkdir(dest_dir)

    if parallel:
        print "Downloading {} images concurrently".format(len(image_urls))
        image_responses = grequests.map([grequests.get(image_url) for image_url in image_urls], size=5, exception_handler=exception_handler)
        at_least_one_failed = False
        for image_resp in image_responses:
            if image_resp is None:
                print "Download failed..."
                at_least_one_failed = True
            else:
                if image_resp.url is None:
                    print image_resp
                dest_path = path.join(dest_dir, path.basename(urlparse(image_resp.url).path))
                print "Saving {} to {}".format(image_resp.url, dest_path)
                image_file = open(dest_path, mode='wb')
                image_file.write(image_resp.content)
                image_file.close()

        if at_least_one_failed:
            for image_url in image_urls:
                dest_path = path.join(dest_dir, path.basename(urlparse(image_url).path))
                if not path.exists(dest_path):
                    print "Download failed for {}".format(image_url)
    else:
        print "Downloading {} images".format(len(image_urls))
        for image_url in image_urls:
            dest_path = path.join(dest_dir, path.basename(urlparse(image_url).path))
            print "Downloading {} to {}".format(image_url, dest_path)
            urlretrieve(image_url, dest_path)



if __name__ == '__main__':
    arguments = docopt(__doc__, version='Get Linked Images 1.0')
    if arguments.get("--just-show-links", False):
        get_image_links_from(arguments["<url>"])
    else:
        download_images_from(arguments["<url>"], parallel = not arguments.get("--serial", False), dir=arguments.get("--dir", None))
