#!/usr/bin/python3
from wdhypermedia import Resource

res = Resource.parse("http://127.0.0.1:5000/")

author_rel = 'http://vocab.example.org/author'
authors_rel = 'http://rels.example.org/authors'
article_rel = 'http://vocab.example.org/article'
articles_rel = 'http://rels.example.org/articles'

# get all authors who have written an article in the article list
for a in res.traverse([articles_rel, article_rel, author_rel]):
    print(a.props["handle"], a.props["website"].uri if "website" in a.props else "")
# print all article titles
for a in res.traverse([articles_rel, article_rel]):
    print(a.props["title"])
