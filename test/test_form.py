from wdhypermedia import Client
from os.path import join, dirname


SEARCH_REL = "http://rels.example.org/search"

test_filepath = join("file://"+dirname(__file__), "html/index.html")
client = Client.from_url(test_filepath)


def test_form():
    form = client.traverse([SEARCH_REL])[0].forms['search']
    assert set(form.params.keys()).issubset({"term", "category"})
    assert form.method == 'get'
    assert "://" in form.action
