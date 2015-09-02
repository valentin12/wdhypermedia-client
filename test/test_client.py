from wdhypermedia import Client, Resource, ResourceList
from os.path import join, dirname


ARTICLES_URI = join("file://"+dirname(__file__), "html/articles.html")
AUTHORS_URI = join("file://"+dirname(__file__), "html/authors.html")
SEARCH_URI = join("file://"+dirname(__file__), "html/search.html")

test_filepath = join("file://"+dirname(__file__), "html/index.html")
client = Client.from_url(test_filepath)


def test_client():
    assert client._root is not None
    assert type(client._root) is Resource
    assert type(client._resources) is dict
    assert all([l in client._resources.keys() for l in [ARTICLES_URI, AUTHORS_URI, SEARCH_URI]])
