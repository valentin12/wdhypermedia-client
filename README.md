# Web Discoverable Hypermedia Client
## Usage
Example server is https://github.com/FND/wdh

```python
import wdhypermedia

# point the client to the root of the API
client = wdhypermedia.Client("http://localhost:5000/")
```

Paths to resources are described by relations, not by links.

```python
# request a list of all authors by describing a path of relations to them
# [resource with list of all authors,  the author resource itself]
authors = client.traverse(["http://rels.example.org/authors",
                           "http://rels.example.org/author"])
# list the authors
for author in authors:
    handle = author.props["handle"][0]
    print(handle, end=" ")
    name = author.props.get("name", [""])[0]
    print(name, end=" ")
    website = author.props.get("website", [None])[0]
    if website:
        print(website.uri, end="")
    print()
```

There is also a very basic support for forms

```python
# use a search form
search_site = client.traverse(["http://rels.example.org/search"])[0]
search_form = search_site.forms["search"]
# print available field names
print(list(search_form.params.keys()))
# set term and category to search for articles containing "hello"
search_form.params["category"] = "article"
search_form.params["term"] = "hello"
# submit the request
result = search_form.submit()
# get all articles in the returned resource
articles = result.traverse(["http://rels.example.org/article"])
for article in articles:
    print(article.props["title"])
```


## More Examples


### Basics

Starting point for an WDH API is a root document, pointing to the different documents important for the client.
The client is looking for the `rel` attribute of the anchor elements, to find its way through the API, even if
links change or other anchors are added. An example `index.html` could look like the following:

A standard HTML document, which contains a self-reference in its `<head>` as a `<link>` tag with `rel="self"`.
The body contains the list to the different documents: A list of articles, a list of authors and a search.

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>index</title>
    <link rel="self" href="/">
</head>
<body>
<h1>index</h1>
<ul>
    <li>
        <a href="/articles" rel="http://rels.example.org/articles">articles</a>
    </li>
    <li>
        <a href="/authors" rel="http://rels.example.org/authors">authors</a>
    </li>
    <li>
        <a href="/search" rel="http://rels.example.org/search">search</a>
    </li>
</ul>
</body>
</html>
```

A `Client` is used to access the document

```python
html_str = "..."
client = Client.from_html(html_str)

# all resources known to the client (key is the URI)
print(client._resources)
# Out:
# {'/': <Resource rel='' uri='/', fetched=True at ...>,
# '/authors': <Resource rel='http://rels.example.org/authors' uri='/authors',
#              fetched=False at ...>,
# '/articles': <Resource rel='http://rels.example.org/articles' uri='/articles',
#               fetched=False at ...>,
# '/search': <Resource rel='http://rels.example.org/search' uri='/search',
#             fetched=False at ...>}

# accessing one of the resources (as said above, by relation):
# get a list of resources with rel=~
author_lists = client.traverse(["http://rels.example.org/authors"])
author_list = author_lists[0]
print(author_list)
# Out: <Resource rel='http://rels.example.org/authors' uri='/authors', fetched=False>
```


### Parsing Properties

A resource document has multiple options to provide its properties.

#### `<dl><dt><dd></dd></dt></dl>`
That construct is used to provide basic types like strings, numbers, booleans, timestamps
and links that aren't resources. The `<dt>` object has an optional `data-type` attribute to describe the type of the
content in the following `<dd>`/`<dd>`s. default data-type is string. Options are:

* null
* boolean: *true* | *false*
* number
* string
* timestamp: `<time datetime="..."></time>`
* link: `<a href="...">...</a>`

A `<dt>` tag can be followed by multiple `<dd>` tags, so every property, even if only one `<dd>` followed, is stored as
list.

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>author</title>
    <link rel="self" href="/authors/jdoe">
</head>
<body>
<article>
    <h1>John Doe (jdoe)</h1>
    <dl>
        <dt>handle</dt>
        <dd>jdoe</dd>
        <dt>name</dt>
        <dd>John Doe</dd>
        <dt data-type="link">website</dt>
        <dd>
            <a href="https://jdoe.example.com/blog/">https://jdoe.example.com/blog/</a>
        </dd>
        <dt data-type="timestamp">join-date</dt>
        <dd>
            <time datetime="2014-01-01">2014/01/01</time>
        </dd>
    </dl>
</article>
</body>
</html>
```

Parsing with the client

```python
html_str = "..."
client = Client.from_html(html_str)
print(client.get_root().props)
# Out:
# {'name': ['John Doe'],
#  'join-date': [datetime.datetime(2014, 1, 1, 0, 0)],
#  'handle': ['jdoe'],
#  'website': [<wdhypermedia.Link at 0x7fe75c1d9240>]}
```


#### (Embedded) Resources

By looking for resources with a specific relation, the client can get resources related to him like
properties, for example an article can list its authors as a list of resources, not in a `<dl>` tag.

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>article</title>
    <link rel="self" href="/articles/0">
</head>
<body>
<article>
    <h1>Hello World</h1>
    <h3>Authors</h3>
    <ul>
        <li>
            <a href="/authors/jdoe"
                    rel="http://rels.example.org/author">
                FND
            </a>
        </li>
        <li>
            <a href="/authors/janedoe"
                    rel="http://rels.example.org/author">
                janedoe
            </a>
        </li>
    </ul>
    <h3>Properties</h3>
    <dl>
        <dt>title</dt>
        <dd>Hello World</dd>
        ...
    </dl>
</article>
</body>
</html>
```

Python code

```python
html_str = "..."
client = Client.from_url(html_str)

# get the 'normal' props
print(client.get_root().props)
# Out:
# {'title': ['Hello World']}

# get the authors by rel
authors = client.traverse(['http://rels.example.org/author'])
for author in authors:
    print(author)
# Out:
# <Resource rel='http://rels.example.org/author' uri='/authors/jdoe', fetched=False>
# <Resource rel='http://rels.example.org/author' uri='/authors/janedoe', fetched=False>
# Right now, they contain if embedded, some, like this, no information. To change this,
# you could do author.fetch() to load the referenced document from the server or just
# try author.props["someprop"]. If "someprop" isn't in author.props, the resource will
# (if it hasn't done so yet) load the document, too.
```


## Not Implemented

* Full support for forms (more input elements, different methods)
* Embedding resources in `<dd>` tags
* Support multiple datetime layouts
* extended HTML in `<dd>` tags
