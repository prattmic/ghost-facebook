# 1. Use Ghost API (requires authentication) to get post contents
#    https://github.com/TryGhost/Ghost/wiki/%5BWIP%5D-API-Documentation

# 2. Convert post content from Markdown to HTML

# 3. Extract images from HTML (with BeautifulSoup)

# 4. Post images to FB using Python SDK
#    https://github.com/pythonforfacebook/facebook-sdk

import argparse
from ghostblog import Ghost, GhostError

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

    print(post)
