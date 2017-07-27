from argparse import ArgumentParser
from collections import defaultdict
from imp import load_source
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


def save_image(url, filename, gallery=None):
  """
  Save the specified image to the disk in an optional gallery folder.
  """
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
      report('%s already exists and was skipped' % path, 3)
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
    report('%s saved (%s)' % (path, url), 3)
    global total_count, gallery_count
    total_count += 1
    if gallery is not None:
      gallery_count[gallery] += 1


def report(message, verbosity=0):
  """
  Print out a console message if the minimum verbosity is met.
  """
  if arguments.verbosity >= verbosity:
    print message


def report_gallery(name):
  """
  Print out a console message indicating the number of images saved in a certain gallery.
  """
  global gallery_count
  if gallery_count[name] > 0:
    report('Saved %(count)s images to "%(title)s"\n' % {
      'count': gallery_count[name],
      'title': name
    })


def parseGeneric(url):
  print 'The Generic scraper is not ready yet, come back later'


def loadParsers():
  """
  Load any python files in the parser directory.
  """
  parser_directory = 'parsers/'
  if not os.path.exists(parser_directory):
    return false
  files = os.listdir(parser_directory)
  modules = dict()
  for file in (x for x in files if x.endswith('.py')):
    name = file.rstrip('.py')
    # https://stackoverflow.com/questions/67631/how-to-import-a-module-given-the-full-path
    module = load_source('%s' % name, parser_directory + file)
    display_name = module.verbose_name if hasattr(module, 'verbose_name') else name
    if not hasattr(module, 'parse'):
      report('=> %s parser not loaded because it lacks the parse() method' % display_name, 3)
    elif not hasattr(module, 'pattern'):
      report('=> %s parser not loaded because it lacks the pattern regex' % display_name, 3)
    else:
      report('=> %s parser loaded' % display_name, 3)
      modules[display_name] = module
  if len(modules) == 0:
    return None
  report('', 3)
  return modules


def chooseParser(domain, modules):
  """
  Search through the list of modules to find one whose pattern matches the
  domain provided. If no matches are found, use the generic parser.
  """
  for name, module in modules.iteritems():
    if module.pattern.search(domain):
      report('Using %s praser\n' % name, 1)
      return module.parse
  report('Using generic parser\n', 1)
  return parseGeneric


def main():
  url = arguments.url
  parsed_url = urlparse(url)
  if not parsed_url.netloc:
    parser.error('The URL provided is not valid')
  global root_url
  root_url = '%s://%s' % (parsed_url.scheme, parsed_url.netloc)

  if arguments.test:
    report('Running in testing mode, no images will be saved\n', 1)

  modules = loadParsers()
  if modules is not None:
    parse_method = chooseParser(parsed_url.netloc, modules)
  else:
    parse_method = parseGeneric

  parse_method(url)

  global total_count
  if total_count > 0:
    parser.exit(message='== Saved a total of %s images ==\n' % total_count)
  else:
    parser.exit(message='== No images were downloaded ==\n')

if __name__ == '__main__':
  main()
