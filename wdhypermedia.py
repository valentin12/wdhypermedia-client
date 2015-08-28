#!/usr/bin/python3
from lxml import html
from urllib import request


class Ressource(object):
    def __init__(self, doc=None, links=None, attrs=None, uri="", rel="", title=""):
        self._links = links if links is not None else []
        self._doc = doc
        self._resolved = False
        if self._doc is not None:
            self._resolved = True
        self._uri = uri
        self._rel = rel
        self._title = title
        if attrs is not None:
            self.__dict__.update(attrs)

    def __str__(self):
        return "<{} _uri='{}', _resolved={}>".format(self.__class__.__name__, self._uri, self._resolved)

    def __repr__(self):
        return "{} at {}>".format(str(self)[:-1], hex(id(self)))

    @staticmethod
    def _extract_links(doc):
        links = {}
        for link in doc.cssselect("a"):
            if "rel" in link.attrib:
                link_obj = Ressource(uri=link.attrib["href"], rel=link.attrib["rel"], title=link.text)
                if link.attrib["rel"] in links:
                    links[link.attrib["rel"]].append(link_obj)
                else:
                    links[link.attrib["rel"]] = [link_obj]
        return links

    @staticmethod
    def _extract_attrs(doc):
        types = {'string': str,
                 'int': int,
                 'boolean': bool,
                 'double': float}
        attrs = {}
        data_lists_raw = doc.cssselect(".typed.xoxo dl")
        dl = []
        for data_list in data_lists_raw:
            dl.extend(data_list.cssselect("*"))
        dl = [e for e in dl if e.tag in ['dt', 'dd']]
        for i in range(len(dl)):
            if dl[i].tag == 'dt':
                attrs[dl[i].text] = dl[i+1].text
        return attrs

    @staticmethod
    def parse(url="", html_str=""):
        if url:
            html_str = request.urlopen(url).read()
        doc = html.fromstring(html_str)
        links = Ressource._extract_links(doc)
        attrs = Ressource._extract_attrs(doc)
        return Ressource(doc=doc, links=links, uri=url, attrs=attrs)

    def resolve(self):
        if not self._resolved:
            html_str = request.urlopen(self._uri).read()
            self._doc = html.fromstring(html_str)
            self._links = Ressource._extract_links(self._doc)
            attrs = Ressource._extract_attrs(self._doc)
            self.__dict__.update(attrs)
            self._resolved = True
        return self

    def traverse(self, rel):
        if not self._resolved:
            self.resolve()
        if rel in self._links:
            return self._links[rel]
        return []
