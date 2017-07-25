from argparse import ArgumentParser
from collections import defaultdict
import json
import os
import re
from urlparse import urlparse

from bs4 import BeautifulSoup
import requests

parser = ArgumentParser(description='A script for downloading images from a website.')
parser.add_argument('url', help='Page to download images from')
parser.add_argument('--dest', '-d', default='images/', metavar='PATH', help='Folder where images should be downloaded')
save_mode = parser.add_mutually_exclusive_group()
save_mode.add_argument('-s', '--skip-duplicates', action='store_true', dest='skip', help='If duplicate images are found, skip over them and continue')
save_mode.add_argument('-o', '--overwrite-duplicates', action='store_true', dest='overwrite', help='If duplicate images are found, overwrite the existing image')
parser.add_argument('--verbose', '-v', action='count', dest='verbosity', help='Use multiple times to increase verbosity')
parser.add_argument('--test', '-t', action='store_true', dest='test', help='Run through the program without saving to disk')
arguments = parser.parse_args()

session = requests.Session()

total_count = 0
gallery_count = defaultdict(int)


def getPath(subfolder=None):
  """
  Get the path provided in the arguments and make sure the provided folder
  exists and is writable.
  """
  path = arguments.dest
  if not path.endswith('/'):
    path = path + '/'
  if subfolder is not None:
    path = '%(path)s%(subfolder)s/' % {
      'path': path,
      'subfolder': subfolder
    }
  if not arguments.test:
    if not os.path.exists(path):
      try:
        os.makedirs(path)
      except:
        parser.error('Destination folder could not be created')
    if not os.access(path, os.W_OK):
      parser.error('Destination folder is not writable')
  return path


def saveImage(url, filename, gallery=None):
  """
  Save the specified image to the disk in an optional gallery folder.
  """
  global total_count, gallery_count
  complete = False
  path = getPath(gallery) + filename

  def generateNewFilePath(path, count=0):
    split = path.rsplit('.', 1)
    count += 1
    if len(split) == 2:
      tmp_path = '%(name)s %(count)s.%(ext)s' % { 'name': split[0], 'count': count, 'ext': split[1] }
    else:
      tmp_path = '%(name)s %(count)s' % { 'name': split[0], 'count': count }
    if os.path.isfile(tmp_path):
      tmp_path = generateNewFilePath(path, count)
    return tmp_path

  if os.path.isfile(path) and not arguments.overwrite:
    if arguments.skip:
      if arguments.verbosity > 2:
        print '%s already exists and was skipped'
      return
    else:
      path = generateNewFilePath(path)

  if not arguments.test:
    image = requests.get(url, stream=True)
    if image.status_code == 200:
      with open(path, 'wb') as file:
        for chunk in image.iter_content(chunk_size=128):
          file.write(chunk)
      complete = True
  else:
    complete = True
  if complete:
    if arguments.verbosity > 2:
      print '%s saved' % path
    total_count += 1
    if gallery is not None:
      gallery_count[gallery] += 1


def scrapePhotoShelter(url):
  if arguments.verbosity > 0:
    print 'Using PhotoShelter scraper\n'

  def getFullResPath(path):
    return re.sub(r'fit=(\/fill=)?(\d+)x(\d+)', 'fit=100000x100000', path)

  def parseImageDetailPage(det_page):
    images = det_page.find_all(class_='imageWidget')
    if not images:
      return False
    try:
      filename = det_page.find(itemprop='name').string
    except:
      filename = None
    for image_path in (x.find('img')['src'] for x in images if x.find('img') is not None):
      if filename is None:
        search_result = re.search(r'\/([\w\d-\.]+)$', image_path)
        image_filename = search_reesult.group(1) if search_result is not None else None
      else:
        image_filename = filename
      saveImage(getFullResPath(image_path), image_filename)

  def parseImageGallery(gal_page):
    if not gal_page.find(class_='thumbsContainer'):
      return
    gallery_header = gal_page.find(class_='galInfo').find('h1')
    gallery_title = gallery_header.string if gallery_header else None
    thumbnails = gal_page.find_all(class_='thumbnail')
    for thumbnail in thumbnails:
      link = thumbnail.a['href']
      if link.startswith('/gallery/') or link.startswith('/gallery-collection/'):
        global root_url
        new_page = session.get(root_url + link, cookies={'thmOpt': '5000%7C0'})
        if new_page.status_code == 200:
          new_soup = BeautifulSoup(new_page.text, 'lxml')
          parseImageGallery(new_soup)
      elif link.startswith('/gallery-image/'):
        img_tag = thumbnail.find('img')
        if not img_tag:
          continue
        image_path = getFullResPath(img_tag['src'])
        data = json.loads(img_tag['data-gal-img-thumb'])
        image_filename = data['I_FILE_NAME'] if data and data['I_FILE_NAME'] else None
        saveImage(image_path, image_filename, gallery_title)

    if gallery_title is not None and gallery_count[gallery_title] > 0 and arguments.verbosity > 1:
      print 'Saved %(count)s images to "%(title)s"\n' % {
        'count': gallery_count[gallery_title],
        'title': gallery_title
      }

  # Set a cookie to ensure all images are loaded in the gallery
  page = session.get(url, cookies={'thmOpt': '5000%7C0'})
  soup = BeautifulSoup(page.text, 'lxml')
  if soup.find(class_='imageWidget'):
    parseImageDetailPage(soup)
  else:
    parseImageGallery(soup)


def scrapeJAlbum(url):
  if arguments.verbosity > 0:
    print 'Using jAlbum scraper\n'
  print 'The jAlbum scraper is not ready yet, come back later'


def scrapeGeneric(url):
  if arguments.verbosity > 0:
    print 'Using generic scraper\n'
  print 'The Generic scraper is not ready yet, come back later'


def main():
  url = arguments.url
  parsed_url = urlparse(url)
  if not parsed_url.netloc:
    parser.error('The URL provided is not valid')
  global root_url
  root_url = '%s://%s' % (parsed_url.scheme, parsed_url.netloc)

  if arguments.test and arguments.verbosity > 0:
    print 'Running in testing mode, no images will be saved'

  if re.search(r'photoshelter\.com', parsed_url.netloc):
    scrapePhotoShelter(url)
  elif re.search(r'jalbum\.net', parsed_url.netloc):
    scrapeJAlbum(url)
  else:
    scrapeGeneric(url)

  if total_count > 0:
    parser.exit(message='== Saved a total of %s images ==\n' % total_count)

if __name__ == '__main__':
  main()
