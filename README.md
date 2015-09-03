# Web Discoverable Hypermedia Client
## Usage
Example server is https://github.com/FND/wdh

    import wdhypermedia
    
    # point the client to the root of the API
    client = wdhypermedia.Client("http://localhost:5000/")
    
Paths to resources are described by relations, not by links.

    # request a list of all authors by describing a path of relations to them
    #                          resource with list of all authors,  the author resource itself
    authors = client.traverse(["http://rels.example.org/authors", "http://rels.example.org/author"])
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
    
There is also a very basic support for forms
    
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