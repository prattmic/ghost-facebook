from __future__ import print_function
import argparse
from bs4 import BeautifulSoup
import facebook
from flask import Flask, request
from ghostblog import Ghost, GhostError
import logging
import requests
import sys

try: # Python 3
    from io import BytesIO
    from urllib.parse import urlencode, urlparse, urlunparse
except ImportError: # Python 2
    from urllib import urlencode
    from urlparse import urlparse, urlunparse
    from cStringIO import StringIO as BytesIO

# Make input behave as in Python 3
if sys.version_info.major == 2:
    input = raw_input

APP_ID = '756432811108370'
APP_SECRET = '0b4b2cb295a2fa539dcb1e50587c7c14'

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

def facebook_access_token(app_id=APP_ID, app_secret=APP_SECRET):
    redirect_uri = 'http://localhost:3000/ghost-facebook/'

    params = {
        'app_id': app_id,
        'redirect_uri': redirect_uri,
        # Access and post photos permissions
        'scope': 'user_photos,publish_actions'
    }

    oauth_url = 'https://www.facebook.com/dialog/oauth?%s' % urlencode(params)
    print("Please direct your browser to: %s" % oauth_url)

    flask_app.run(port=3000)
    logging.debug('Got code: %s' % code)

    return facebook.get_access_token_from_code(code, redirect_uri,
                                               app_id, app_secret)

def upload_to_facebook(fb, uri):
    """
    Download image from URI and upload it to FB.
    """
    image = requests.get(uri)
    image = BytesIO(image.content)

    fb.put_photo(image)

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Post images from Ghost blog to Facebook')
    parser.add_argument('ghost_url', help='URL of Ghost blog to extract images from')
    parser.add_argument('ghost_username', help='Username of Ghost user')
    parser.add_argument('ghost_password', help='Password of Ghost user')
    parser.add_argument('--post-id', '-i', type=int, default=None,
                        help='''ID of post to extract from.  By default,
                                the latest post is used.''')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    post = ghost_download_post(args.ghost_url, args.ghost_username,
                               args.ghost_password, args.post_id)

    imgs = find_local_images(post['html'], args.ghost_url)

    print('Images to upload:')
    for img in imgs:
        print('\t* %s' % img)

    cont = input('Continue? (y/N)')
    if cont != 'y':
        print('Aborting')
        exit(1)

    token = facebook_access_token()

    fb = facebook.GraphAPI(token['access_token'])

    for img in imgs:
        print('Uploading %s ...' % img, end='')
        upload_to_facebook(fb, img)
        print('Done.')
