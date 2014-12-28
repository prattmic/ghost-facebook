Post photos from a [Ghost](https://github.com/TryGhost/Ghost) blog to Facebook
==============================================================================

Uses [ghostblog](https://github.com/prattmic/ghostblog) to fetch posts from a
Ghost blog, extracts images hosted on the same domain as the blog, then using
[facebook-sdk](https://github.com/pythonforfacebook/facebook-sdk) to post each
photo to Facebook.

Your [Facebook App](https://developers.facebook.com/apps/) ID and secret must
either be provided as arguments, or placed in `config.json`, as in
`config.example.json`.
