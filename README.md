Post photos from a [Ghost](https://github.com/TryGhost/Ghost) blog to Facebook
==============================================================================

Uses [ghostblog](https://github.com/prattmic/ghostblog) to fetch posts from a
Ghost blog, extracts images hosted on the same domain as the blog, then using
[facebook-sdk](https://github.com/pythonforfacebook/facebook-sdk) to post each
photo to Facebook.

For authentication through the Facebook SDK, this application will temporarily
run an HTTP server listening on port 5000, which must be exposed on the
`/ghost-facebook/` URI.  This will be passed as the redirect URI to Facebook,
which will redirect the user back, providing the application with the user's
authentication code.

You must provide the URL, username (email), and password of your Ghost blog,
your [Facebook App](https://developers.facebook.com/apps/) ID and secret, and
the domain this application's server will be exposed on.  These can either be
provided as arguments, or placed in `config.json`, as in `config.example.json`.
