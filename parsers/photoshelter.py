import json
import re
from urlparse import urlparse

from bs4 import BeautifulSoup
import requests

from scrape import report, report_gallery, save_image


verbose_name = 'PhotoShelter'
pattern = re.compile(r'photoshelter\.com')

def get_full_res_path(path):
  """
  Return the path to the highest resolution image available.
  """
  return re.sub(r'fit=(\/fill=)?(\d+)x(\d+)', 'fit=100000x100000', path)


def parse_image_page(page):
  images = page.find_all(class_='imageWidget')
  if not images:
    return False
  try:
    filename = page.find(itemprop='name').string
  except:
    filename = None
  for image_path in (x.find('img')['src'] for x in images if x.find('img') is not None):
    if filename is None:
      search_result = re.search(r'\/([\w\d-\.]+)$', image_path)
      image_filename = search_reesult.group(1) if search_result is not None else None
    else:
      image_filename = filename
    save_image(get_full_res_path(image_path), image_filename)


def parse_gallery_page(page):
  if not page.find(class_='thumbsContainer'):
    return
  gallery_header = page.find(class_='galInfo').find('h1')
  gallery_title = gallery_header.string if gallery_header else None
  thumbnails = page.find_all(class_='thumbnail')
  global root_url
  for thumbnail in thumbnails:
    link = thumbnail.a['href']
    if link.startswith('/gallery/') or link.startswith('/gallery-collection/'):
      new_page = requests.get(root_url + link, cookies={'thmOpt': '5000%7C0'})
      if new_page.status_code == 200:
        new_soup = BeautifulSoup(new_page.text, 'lxml')
        parse_gallery_page(new_soup)
    elif link.startswith('/gallery-image/'):
      img_tag = thumbnail.find('img')
      if not img_tag:
        continue
      image_path = get_full_res_path(img_tag['src'])
      data = json.loads(img_tag['data-gal-img-thumb'])
      image_filename = data['I_FILE_NAME'] if data and data['I_FILE_NAME'] else None
      save_image(image_path, image_filename, gallery_title)

  if gallery_title is not None:
    report_gallery(gallery_title)


def parse(url):
  global root_url
  parsed_url = urlparse(url)
  root_url = '%s://%s' % (parsed_url.scheme, parsed_url.netloc)

  # Set a cookie to ensure all images are loaded in the gallery
  page = requests.get(url, cookies={'thmOpt': '5000%7C0'})
  soup = BeautifulSoup(page.text, 'lxml')
  if soup.find(class_='imageWidget'):
    parse_image_page(soup)
  else:
    parse_gallery_page(soup)
