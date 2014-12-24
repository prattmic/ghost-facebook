# 1. Use Ghost API (requires authentication) to get post contents
#    https://github.com/TryGhost/Ghost/wiki/%5BWIP%5D-API-Documentation

# 2. Convert post content from Markdown to HTML

# 3. Extract images from HTML (with BeautifulSoup)

# 4. Post images to FB using Python SDK
#    https://github.com/pythonforfacebook/facebook-sdk

import argparse
from bs4 import BeautifulSoup
from ghostblog import Ghost, GhostError

try: # Python 3
    from urllib.parse import urlparse, urlunparse
except ImportError:
    from urlparse import urlparse, urlunparse

def download_post(url, username, password, post_id=None):
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

    args = parser.parse_args()

    post = download_post(args.ghost_url, args.ghost_username,
                         args.ghost_password, args.post_id)

    imgs = find_local_images(post['html'], args.ghost_url)

    print(imgs)
