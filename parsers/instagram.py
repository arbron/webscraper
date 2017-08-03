import json
import re

from bs4 import BeautifulSoup
import requests

from scrape import report, report_gallery, save_image

verbose_name = 'Instagram'
pattern = re.compile(r'instagram\.com')


def get_shared_data(page):
  result = re.search(r'\<script [^>]+\>window\._sharedData = ([^<]+);\<\/script\>', page.text)
  if not result:
    return False
  return json.loads(result.group(1))


def parse_image_page(data):
  base = data['entry_data']['PostPage'][0]['graphql']['shortcode_media']
  if base['__typename'] == 'GraphImage':
    path = base['display_url']
  elif base['__typename'] == 'GraphVideo':
    path = base['video_url']
  else:
    return
  filename = base['shortcode'] + '.' + path.rsplit('.', 1)[1]
  username = base['owner']['username']
  save_image(path, filename, username)


def parse_user_page(data):
  base = data['entry_data']['ProfilePage'][0]['user']
  username = base['username']
  for image in base['media']['nodes']:
    if image['__typename'] == 'GraphVideo':
      video_url = 'http://%s/p/%s/' % (data['hostname'], image['code'])
      parse(video_url)
    else:
      image_path = image['display_src']
      image_filename = image['code'] + '.' + image_path.rsplit('.', 1)[1]
      save_image(image_path, image_filename, username)


def parse_feed_page(data):
  report('Prase feed page')


def parse(url):
  page = requests.get(url)
  soup = BeautifulSoup(page.text, 'lxml')
  data = get_shared_data(page)

  if 'PostPage' in data['entry_data']:
    parse_image_page(data)
  elif 'ProfilePage' in data['entry_data']:
    parse_user_page(data)
  elif 'FeedPage' in data['entry_data']:
    parse_feed_page(data)
  else:
    report('Unable to identify this page on Instagram')
