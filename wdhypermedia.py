#!/usr/bin/python3
from lxml import html
from urllib import request
from urllib.parse import urljoin

import datetime


class Resource(object):

    def __init__(self, client, doc=None, links=None, props=None, uri="", rel="", title="", embed_doc=None):
        if client:
            self._client = client
        else:
            self._client = Client.from_resource(self)
        self._links = links if links is not None else []
        self._resolved = False
        if doc is not None:
            self._doc = doc
            self._resolved = True
        elif embed_doc is not None:
            self._doc = embed_doc
            self._resolved = False
        self._uri = uri
        self._rel = rel
        self._title = title
        self.props = PropertyList(self._missing_property_handler)
        if props is not None:
            self.props.update(props)

    def __str__(self):
        return "<{} _uri='{}', _resolved={}>".format(self.__class__.__name__, self._uri, self._resolved)

    def __repr__(self):
        return "{} at {}>".format(str(self)[:-1], hex(id(self)))

    def _missing_property_handler(self, props, key):
        if not self._resolved:
            self.fetch()
        if key in props:
            return props[key]
        raise KeyError("'{}'".format(key))

    @staticmethod
    def _get_uri(uri, base_uri):
        return uri if "://" in uri else urljoin(base_uri, uri)

    @staticmethod
    def _extract_links(client, base_uri, doc):
        links = {}
        for link in doc.cssselect("a"):
            if "rel" in link.attrib and link.attrib["rel"] != "self":
                href = Resource._get_uri(link.attrib['href'], base_uri)
                # find an <article> that belongs to the link
                article = link.getnext()
                while article is not None:
                    if article.tag == 'article':
                        break
                    article = article.getnext()
                if article is not None:
                    link_obj = client.get_resource(href, default=Resource.parse_embed(client,
                                                                                      article,
                                                                                      uri=href,
                                                                                      rel=link.attrib["rel"],
                                                                                      title=link.text))
                else:
                    link_obj = client.get_resource(href, default=Resource(client, uri=href, rel=link.attrib["rel"],
                                                                          title=link.text))
                if link.attrib["rel"] in links:
                    links[link.attrib["rel"]].append(link_obj)
                else:
                    links[link.attrib["rel"]] = ResourceList([link_obj])
        return links

    @staticmethod
    def _extract_props(doc, self_uri):
        props = {}
        data_lists_raw = Resource._strip_doc_for_data(doc, self_uri).cssselect("dl")
        dl = []
        for data_list in data_lists_raw:
            dl.extend(data_list.cssselect("*"))
        dl = [e for e in dl if e.tag in ['dt', 'dd']]
        for i in range(len(dl)):
            if dl[i].tag == 'dt':
                res = None  # result
                if "data-type" in dl[i].attrib:
                    if dl[i].attrib["data-type"] == "boolean":
                        res = dl[i+1].text.strip().lower() == "true"
                    elif dl[i].attrib["data-type"] == "number":
                        res = float(dl[i+1].text.strip())
                    elif dl[i].attrib["data-type"] == "null":
                        res = None
                    elif dl[i].attrib["data-type"] == "string":
                        if len(dl[i+1]):
                            # element has children
                            print("Warning: string data contains HTML elements, use \"\"")
                            res = ""
                        else:
                            res = dl[i+1].text
                    elif dl[i].attrib["data-type"] == "link":
                        link_el = dl[i+1].cssselect("a")[0]
                        link_caption = link_el.text
                        link_uri = "" if "href" not in link_el.attrib else link_el.attrib["href"]
                        link_rel = "" if "rel" not in link_el.attrib else link_el.attrib["rel"]
                        res = Link(caption=link_caption, uri=link_uri, rel=link_rel)
                    elif dl[i].attrib["data-type"] == "timestamp":
                        time_el = dl[i+1].cssselect("time")[0]
                        res = datetime.datetime.strptime(time_el.attrib["datetime"], "%Y-%m-%d")
                    else:
                        print("Invalid data type: {}".format(dl[i].attrib["data-type"]))
                else:
                    res = Resource._get_prop(dl[i+1])
                props[dl[i].text] = res
        return props

    @staticmethod
    def _get_prop(dd_e):
        if len(dd_e):
            # element has children
            lists = dd_e.cssselect("ul,ol")
            if len(lists):
                res_list = []
                list_el = lists[0]
                entries = list_el.cssselect("li")
                for entry in entries:
                    res_list.append(Resource._get_prop(entry))
                return res_list
            links = dd_e.cssselect("a")
            if len(links):
                link_el = links[0]
                link_caption = link_el.text.strip()
                link_uri = "" if "href" not in link_el.attrib else link_el.attrib["href"].strip()
                link_rel = "" if "rel" not in link_el.attrib else link_el.attrib["rel"].strip()
                return Link(caption=link_caption, uri=link_uri, rel=link_rel)
            times = dd_e.cssselect("time")
            if len(times):
                time_el = times[0]
                return datetime.datetime.strptime(time_el.attrib["datetime"].strip(), "%Y-%m-%d")
        return dd_e.text.strip()

    @staticmethod
    def _extract_doc_link(doc, default, base_uri):
        try:
            head_link = doc.cssselect("head link")[0]
            return Resource._get_uri(head_link.attrib["href"], base_uri)
        except IndexError:
            return default

    @staticmethod
    def _strip_doc_for_data(doc, self_uri):
        # copy document -> not affecting original
        strip_doc = doc.__copy__()

        # find all embeds (indicated by rel='self') and get their roots (<article>)
        embeds = Resource._get_embeds(strip_doc, self_uri)
        for e in embeds.values():
            # remove from document
            e.getparent().remove(e)
        return strip_doc

    @staticmethod
    def _get_embeds(doc, self_uri):
        embeds = {Resource._get_uri(e.attrib['href'], self_uri): e
                  for e in doc.cssselect("a[rel='self']")
                  if Resource._get_uri(e.attrib['href'], self_uri) != self_uri}
        for key in embeds.keys():
            while embeds[key].tag != 'article':
                embeds[key] = embeds[key].getparent()
        return embeds

    @staticmethod
    def parse(client, url="", html_str=""):
        if url:
            html_str = request.urlopen(url).read()
        doc = html.fromstring(html_str)
        uri = Resource._extract_doc_link(doc, url, url)
        links = Resource._extract_links(client, url, doc)
        props = Resource._extract_props(doc, uri)
        return Resource(client, doc=doc, links=links, uri=uri, props=props)

    @staticmethod
    def parse_embed(client, element, uri="", rel="", title=""):
        uri = Resource._get_uri(element.cssselect("a[rel='self']")[0].attrib['href'], uri)
        links = Resource._extract_links(client, uri, element)
        props = Resource._extract_props(element, uri)
        return Resource(client, embed_doc=element, links=links, uri=uri, rel=rel, title=title, props=props)

    def fetch(self):
        if not self._resolved:
            html_str = request.urlopen(self._uri).read()
            self._doc = html.fromstring(html_str)
            self._links = Resource._extract_links(self._client, self._uri, self._doc)
            props = Resource._extract_props(self._doc, self._uri)
            self.props.update(props)
            self._resolved = True
        return self

    def traverse(self, rels):
        if not self._resolved:
            self.fetch()
        if rels[0] in self._links:
            if len(rels) > 1:
                return self._links[rels[0]].traverse(rels[1:])
            return self._links[rels[0]]
        return ResourceList()


class ResourceList(list):
    def traverse(self, rels):
        ret = ResourceList()
        for res in self:
            ret += res.traverse(rels)
        return ret


class PropertyList(dict):
    def __init__(self, missing_handler, **kwargs):
        super().__init__(**kwargs)
        self.missing_handler = missing_handler

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            return self.missing_handler(self, key)


class Link(object):
    def __init__(self, uri="", caption="", rel=""):
        self.uri = uri
        self.caption = caption
        self.rel = rel


class Client(object):
    def __init__(self, root_url="", root_html_str="", root=None):
        self._root = root
        self._resources_list = []
        if root is None and (root_url or root_html_str):
            self._root = Resource.parse(self, url=root_url, html_str=root_html_str)
        if self._root is not None:
            self._resources_list.append(self._root)

    @property
    def _resources(self):
        res_dict = {}
        for res in self._resources_list:
            res_dict[res._uri] = res
        return res_dict

    def traverse(self, rels):
        return self._root.traverse(rels)

    def get_resource(self, uri, default=None, fetch=False):
        if uri in self._resources:
            if fetch:
                self._resources[uri].fetch()
            return self._resources[uri]
        if default is None:
            raise KeyError("Resource not found and no default provided: {}".format(uri))
        self._resources_list.append(default)
        if fetch:
            default.fetch()
        return default

    @staticmethod
    def from_url(url):
        return Client(root_url=url)

    @staticmethod
    def from_html(html_str):
        return Client(root_html_str=html_str)

    @staticmethod
    def from_resource(resource):
        return Client(root=resource)
