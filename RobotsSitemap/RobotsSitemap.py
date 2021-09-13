#!/usr/bin/env python
import requests
import re
import xml.etree.ElementTree as ET
import sqlite3
from time import time
from datetime import datetime


class SiteAutoTwitter(object):
    """Scrapes urls from sitemaps and instead of tweeting them, just makes record in the log file"""
    def __init__(self):
        self.con = sqlite3.connect('usedurls.db', detect_types=sqlite3.PARSE_DECLTYPES) # Create or connect database
        self.cur = self.con.cursor()
        self.cur.execute('CREATE TABLE IF NOT EXISTS urls (id INTEGER PRIMARY KEY, url TEXT UNIQUE, unixtime REAL);')

    def download_urls(self, site):
        """Copy URLs fron sitemap to the data base"""
        try:
            response = requests.get(site + '/robots.txt')
            response.raise_for_status()
        except:
            print('ERROR! {}/robots.txt is missing.'.format(site))
            return
        
        pattern = re.compile(r'^Sitemap: .+$', re.MULTILINE)
        res = pattern.findall(response.text)
        url_count, nonuniq_count = 0, 0
        for idx, line in enumerate(res):
            match = re.match(r'^Sitemap: (\S+)\s*$', line)
            response = requests.get(match.group(1))
            stripped = response.text[response.text.index('<'):] # Strip bad characters before <, if present
            xml_string = re.sub(r''' xmlns.*(["'])[^\1]*\1''', '', stripped) # Remove namespace data (dirty hack)
            tree = ET.fromstring(xml_string)
            # print([elem.text for elem in tree.iter(tag='loc')])
            for elem in tree.iter(tag='loc'):
                try:
                    self.cur.execute('INSERT INTO urls (url) VALUES (?);', (elem.text,)) # Insert raw
                    url_count += 1
                except sqlite3.IntegrityError: nonuniq_count += 1

        self.con.commit()
        print('{} URLs were successfully obtained from {}.'.format(url_count, site))
        if nonuniq_count > 0: print('{} Non-unique URLs were detected.'.format(nonuniq_count))

    def random_tweet(self, maxtweet):
        """Not actually tweeting, just making a log"""
        urls = self.cur.execute('SELECT id, url FROM urls WHERE unixtime IS NULL ORDER BY RANDOM() LIMIT ?', (maxtweet,)).fetchall()

        with open('tweeted_urls.txt', 'a') as myfile:
            for id_, url in urls:
                timestamp = time()
                self.cur.execute('UPDATE urls SET unixtime = ? WHERE id = ?', (timestamp, id_))
                myfile.write('{} \t{}\n'.format(datetime.fromtimestamp(timestamp), url))

        self.con.commit()
        print('{} URLs were successfully tweeted.'.format(len(urls)))


if __name__ == '__main__':
    sat = SiteAutoTwitter()

    mode = input('Type "U" to get new URLs, type "t" for tweeting: ')
    if mode == 'U': sat.download_urls(input('Enter site address: '))
    elif mode == 't': sat.random_tweet(input('Enter max number of tweets: '))

    # site = 'https://www.youtube.com'
    # site = 'https://focus.ua'
    # site = 'https://fossdoc.com'
    # sat.download_urls(site)
    # sat.random_tweet(1e6)
