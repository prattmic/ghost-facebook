from __future__ import print_function
import argparse
from bs4 import BeautifulSoup
import exifread
import facebook
from flask import Flask, request
from ghostblog import Ghost, GhostError
import json
import logging
import requests
import sys

try: # Python 3
    from io import BytesIO
    from urllib.parse import urlencode, urljoin, urlparse, urlunparse
except ImportError: # Python 2
    from urllib import urlencode
    from urlparse import urljoin, urlparse, urlunparse
    from cStringIO import StringIO as BytesIO

# Make input behave as in Python 3
if sys.version_info.major == 2:
    input = raw_input

FLASK_PORT = 5000   # Flask listening port

# Facebook authentication flow:

# 1. User browses to /dialog/oauth, which has additional app ID and redirect
#    parameters
# 2. The user approves the app, and is redirected to the provided redirect URL
# 3. The Flask app listens on the redirect URL.  The request contains a special
#    code from Facebook.
# 4. The server (this application), uses the code to request an access token
#    from Facebook.
# 5. All further requests use the access token for authentication.

# Temporary web server to receive code from Facebook
#
# With Flask, there is no way to listen for one request, so when the user is
# pointed to FB, the Flask server is started, listening for the redirect
# callback.  When the callback is received, the code is retrieved and placed in
# the global.  The server is then shutdown, allowing the main application flow
# to continue.

flask_app = Flask(__name__)
code = None

def shutdown_flask():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

@flask_app.route('/ghost-facebook/')
def oauth_callback():
    global code
    code = request.args.get('code', '')
    shutdown_flask()
    return 'Success'

def facebook_access_token(domain, app_id, app_secret):
    redirect_uri = urljoin(domain, '/ghost-facebook/')

    params = {
        'app_id': app_id,
        'redirect_uri': redirect_uri,
        # Access and post photos permissions
        'scope': 'user_photos,publish_actions'
    }

    oauth_url = 'https://www.facebook.com/dialog/oauth?%s' % urlencode(params)
    print("Please direct your browser to: %s" % oauth_url)

    flask_app.run(port=FLASK_PORT)
    logging.debug('Got code: %s' % code)

    return facebook.get_access_token_from_code(code, redirect_uri,
                                               app_id, app_secret)

def upload_to_facebook(fb, uri, album, post_url):
    """
    Download image from URI and upload it to FB.
    """
    image = requests.get(uri)
    image = BytesIO(image.content)

    tags = exifread.process_file(image)

    if 'Image ImageDescription' in tags:
        description = tags['Image ImageDescription'].values
        description += '\n\n'
    else:
        description = ''

    # Image must be reread from beginning for upload
    image.seek(0)

    description += post_url

    fb.put_photo(image, album_id=album, message=description)

def ghost_download_post(url, username, password, post_id=None):
    """
    Get post id from Ghost blog.

    If no id is specified, the latest post is retrieved.
    """
    ghost = Ghost(url, username, password)
    posts = ghost.posts(post_id)

    if 'errors' in posts:
        raise GhostError(posts['errors'][0]['message'])

    # First result is either the requested post ID, or the latest post
    return posts['posts'][0]

def ghost_post_url(ghost_url, post):
    """
    Absolute web address of Ghost post.
    """
    # Base URL should be an absolute folder
    if not ghost_url.endswith('/'):
        ghost_url += '/'

    # Post URL should be relative
    post_url = post['url']
    if post_url.startswith('/'):
        post_url = post_url[1:]

    return urljoin(ghost_url, post_url)

def find_local_images(html, base_uri):
    """
    Find all images referenced in HTML that are on the base_uri domain.

    For example, with a base URL of example.com, these would match:
        * example.com/image.png
        * /image.png

    But 'example.org/image.png' would not.

    A list of absolute URIs will be returned.
    """
    base_uri = urlparse(base_uri)
    uris = []

    b = BeautifulSoup(html)
    imgs = b.findAll('img')

    for img in imgs:
        uri = urlparse(img['src'])

        # Is URI on this domain?
        # It either has no netloc, and is an absolute,
        # or it does has a netloc, and is an absolute uri.
        if uri.netloc and uri.netloc != base_uri.netloc:
            continue

        # Copy from base if not included in uri
        if not uri.netloc:
            uri = uri._replace(scheme=base_uri.scheme, netloc=base_uri.netloc)

        uris.append(urlunparse(uri))

    return uris

class MissingArgumentError(Exception):
    def __init__(self, argument, *args, **kwargs):
        message = 'Missing %s; pass as argument, or in config.json.' \
                    % (argument,)
        super(MissingArgumentError, self).__init__(message, *args, **kwargs)

def process_config(args):
    """
    Read config from the config file and the command line, returning the
    final configuration.  Command line options override config file options.
    """
    # Turn argparse object into a dictionary to make it easier to work with
    args = vars(args)

    config = {}

    # First, try to load config from a file
    try:
        config = json.load(open(args['config']))
    except IOError:
        pass

    # Then, override with command-line options
    for key in args:
        # If key wasn't set by file, add it from the command line
        # argument, even if the value is None.  This ensures that
        # the config dictionary will have an entry for all arguments.
        if args[key] or not key in config:
            config[key] = args[key]

    # If domain is not provided, a default on localhost is used
    if not config['domain']:
        config['domain'] = 'http://localhost:%d' % FLASK_PORT

    # Make sure required args have been set from the file or command line
    required_args = ['ghost_url', 'ghost_username', 'ghost_password',
                     'app_id', 'app_secret']

    for arg in required_args:
        if arg not in config or not config[arg]:
            raise MissingArgumentError(arg)

    return config

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Post images from Ghost blog to Facebook')
    parser.add_argument('--ghost-url', help='URL of Ghost blog to extract images from')
    parser.add_argument('--ghost-username', help='Username of Ghost user')
    parser.add_argument('--ghost-password', help='Password of Ghost user')
    parser.add_argument('--post-id', '-i', type=int, default=None,
                        help='''ID of post to extract from.  By default,
                                the latest post is used.''')
    parser.add_argument('--app-id', help='Facebook app id')
    parser.add_argument('--app-secret', help='Facebook app secret')
    parser.add_argument('--domain', '-d', default=None,
                        help='''Base domain of local server, passed to Facebook
                                in redirect URI.''')
    parser.add_argument('--album-id', help='Facebook photo album to post photos to')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--config', '-c', default='config.json',
                        help='JSON file with default values for each argument.')

    args = parser.parse_args()
    config = process_config(args)

    if config['verbose']:
        logging.basicConfig(level=logging.DEBUG)

    logging.debug('Configuration: %s' % config)

    post = ghost_download_post(config['ghost_url'], config['ghost_username'],
                               config['ghost_password'], config['post_id'])

    post_url = ghost_post_url(config['ghost_url'], post)
    print('Post: %s' % post_url)

    imgs = find_local_images(post['html'], config['ghost_url'])

    print('Images to upload:')
    for img in imgs:
        print('\t* %s' % img)

    cont = input('Continue? (y/N) ')
    if cont != 'y':
        print('Aborting')
        exit(1)

    token = facebook_access_token(config['domain'], config['app_id'],
                                  config['app_secret'])

    fb = facebook.GraphAPI(token['access_token'])

    for img in imgs:
        print('Uploading %s ...' % img, end='')
        upload_to_facebook(fb, img, config['album_id'], post_url)
        print(' Done.')
