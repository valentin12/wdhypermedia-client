from wdhypermedia import Resource, ResourceList, Client
from os.path import join, dirname


ARTICLES_REL = 'http://rels.example.org/articles'
AUTHORS_REL = 'http://rels.example.org/authors'
SEARCH_REL = 'http://rels.example.org/search'

test_filepath = join("file://"+dirname(__file__), "html/index.html")
cl = Client()
res = Resource.parse(cl, test_filepath)
articles = res.traverse([ARTICLES_REL])


def test_res():
    assert res._uri == test_filepath
    assert res._doc is not None
    assert res._resolved == True


def test_parse():
    assert len(res.props) == 0
    assert all([l in res._links.keys() for l in [ARTICLES_REL, AUTHORS_REL, SEARCH_REL]])
    assert type(res._links['http://rels.example.org/articles'][0]) is Resource


def test_traverse():
    assert type(articles) is ResourceList
    assert len(articles) == 1
    assert type(articles[0]) is Resource
    assert articles[0]._resolved == False
    assert articles[0]._rel == ARTICLES_REL
    assert articles[0]._title == "articles"
