#!/usr/bin/python3
from lxml import html
from urllib import request
from urllib.parse import urljoin, urlparse, urlunparse, urlencode

import datetime


class Resource(object):
    """
    Stores all information belonging to a resource referred to by an URI
    """

    def __init__(self, client, doc=None, links=None, props=None, forms=None, uri="", rel="", title="", embed_doc=None):
        if client:
            self._client = client
        else:
            self._client = Client.from_resource(self)
        self._resolved = False
        if doc is not None:
            self._doc = doc
            self._resolved = True
        elif embed_doc is not None:
            self._doc = embed_doc
            self._resolved = False
        self.uri = uri
        self._rel = rel
        self._title = title
        self._links = links if links is not None else []
        self.forms = PropertyList(self._missing_property_handler)
        if forms is not None:
            self.forms.update(forms)
        self.props = PropertyList(self._missing_property_handler)
        if props is not None:
            self.props.update(props)

    def __str__(self):
        return "<{} _uri='{}', _resolved={}>".format(self.__class__.__name__, self.uri, self._resolved)

    def __repr__(self):
        return "{} at {}>".format(str(self)[:-1], hex(id(self)))

    def _missing_property_handler(self, props, key):
        if not self._resolved:
            self.fetch()
        if key in props:
            return props[key]
        raise KeyError("'{}'".format(key))

    @staticmethod
    def from_uri(client, uri=""):
        """
        Parse an resource located at the uri and turn it into an Resource object

        :param client: Client to which this Resource belongs to
        :param uri: pointing to the resource
        :return: The created Resource object
        """
        try:
            return client.get_resource(uri, fetch=True)
        except KeyError:
            html_str = request.urlopen(uri).read()
        return Resource.from_html(client, html_str, base_uri=uri)

    @staticmethod
    def from_html(client, html_str, base_uri=""):
        """
        Parse an HTML string and turn it into a Resource object

        :param client: Client to which this Resource belongs to
        :param html_str: The resource as HTML string
        :param base_uri: (optional) Base uri to resolve relative URIs
        """
        doc = html.fromstring(html_str)
        uri = extract_doc_link(doc, base_uri, base_uri)
        try:
            return client.get_resource(uri, fetch=True)
        except KeyError:
            links = extract_links(client, base_uri, doc)
            props = extract_props(doc, uri)
            forms = extract_forms(client, doc, uri)
            res = Resource(client, doc=doc, links=links, uri=uri, props=props, forms=forms)
            client.add_resource(res)
            return res

    @staticmethod
    def _parse_embed(client, element, uri="", rel="", title=""):
        """
        Parse an embedded resource

        :param client: Client to which this Resource belongs to
        :param element: Element containing the embedded resource
        :param uri: (optional) pointing to the resource
        :param rel: (optional) relation belonging to the resource
        :param title: (optional) describing the resource
        """
        uri = get_uri(element.cssselect("summary a".format(rel))[0].attrib['href'], uri)
        try:
            client.get_resource(uri, fetch=True)
        except KeyError:
            links = extract_links(client, uri, element)
            props = extract_props(element, uri)
            forms = extract_forms(client, element, uri)
            res = Resource(client, embed_doc=element,
                           links=links, uri=uri, rel=rel, title=title, props=props, forms=forms)
            client.add_resource(res)
            return res

    @staticmethod
    def link(client, uri, rel="", title=""):
        """
        Create a resource pointing to an uri

        :param client: Client to which this Resource belongs to
        :param uri: pointing to the resource
        :param rel: relation belonging to the resource
        :param title: describing the resource
        """
        if uri:
            try:
                res = client.get_resource(uri)
                res._title = title
            except KeyError:
                pass
        res = Resource(client, uri=uri, rel=rel, title=title)
        client.add_resource(res)
        return res

    def fetch(self, update=False):
        """
        Fetching and parsing the document of the resource

        :param update: Fetch, even if the resource was already fetched
        """
        if not self._resolved or update:
            html_str = request.urlopen(self.uri).read()
            self._doc = html.fromstring(html_str)
            self._links = extract_links(self._client, self.uri, self._doc)
            self.forms.update(extract_forms(self._client, self._doc, self.uri))
            self.props.update(extract_props(self._doc, self.uri))
            self._resolved = True
        return self

    def update(self):
        """
        Refetch the resource

        equals fetch(update=True)
        """
        self.fetch(update=True)

    def traverse(self, rels):
        """
        Get the resources described by a path of relations
        relative to this resource

        :param rels: List of relations as strings
        :return: ResourceList of the resources found
        """
        if not self._resolved:
            self.fetch()
        if rels[0] in self._links:
            if len(rels) > 1:
                return self._links[rels[0]].traverse(rels[1:])
            return self._links[rels[0]]
        return ResourceList()


def get_uri(uri, base_uri):
    return uri if "://" in uri else urljoin(base_uri, uri)


def extract_props(doc, self_uri):
    """
    Extract properties for the current document.
    Means: Every <dl> which isn't embedded in another resource

    :param doc: Current document/element
    :param self_uri: uri of the resource
    :return: A dictionary of the parsed properties (key: <dt>, value:<dd>)
    """
    props = {}
    data_lists_raw = strip_doc_for_data(doc, self_uri).cssselect("dl")
    dl = []
    for data_list in data_lists_raw:
        dl.extend(data_list.cssselect("*"))
    dl = [e for e in dl if e.tag in ['dt', 'dd']]
    for i in range(len(dl)):
        if dl[i].tag == 'dt':
            dd_count = 0
            while len(dl) > i + dd_count + 1 and dl[i+dd_count+1].tag == 'dd':
                dd_count += 1
            res = []  # result
            if "data-type" in dl[i].attrib:
                for dd_num in range(dd_count):
                    if dl[i].attrib["data-type"] == "boolean":
                        res.append(dl[i+dd_num+1].text.strip().lower() == "true")
                    elif dl[i].attrib["data-type"] == "number":
                        res.append(float(dl[i+dd_num+1].text.strip()))
                    elif dl[i].attrib["data-type"] == "null":
                        res.append(None)
                    elif dl[i].attrib["data-type"] == "string":
                        if len(dl[i+dd_num+1]):
                            # element has children
                            print("Warning: string data contains HTML elements, use \"\"")
                            res.append("")
                        else:
                            res.append(dl[i+1].text)
                    elif dl[i].attrib["data-type"] == "link":
                        link_el = dl[i+1].cssselect("a")[0]
                        link_caption = link_el.text
                        link_uri = "" if "href" not in link_el.attrib else link_el.attrib["href"]
                        link_rel = "" if "rel" not in link_el.attrib else link_el.attrib["rel"]
                        res.append(Link(caption=link_caption, uri=link_uri, rel=link_rel))
                    elif dl[i].attrib["data-type"] == "timestamp":
                        time_el = dl[i+1].cssselect("time")[0]
                        res.append(datetime.datetime.strptime(time_el.attrib["datetime"], "%Y-%m-%d"))
                    else:
                        print("Invalid data type: {}".format(dl[i].attrib["data-type"]))
            else:
                for dd_num in range(dd_count):
                    res.append(get_prop(dl[i+1]))
            props[dl[i].text] = res
    return props


def get_prop(dd_element):
    """
    Extract property from one element when data-type is unknown

    :param dd_element: The element to extract from
    :return: content of the element
    """
    if len(dd_element):
        # element has children
        lists = dd_element.cssselect("ul,ol")
        if len(lists):
            res_list = []
            list_el = lists[0]
            entries = list_el.cssselect("li")
            for entry in entries:
                res_list.append(get_prop(entry))
            return res_list
        links = dd_element.cssselect("a")
        if len(links):
            link_el = links[0]
            link_caption = link_el.text.strip()
            link_uri = "" if "href" not in link_el.attrib else link_el.attrib["href"].strip()
            link_rel = "" if "rel" not in link_el.attrib else link_el.attrib["rel"].strip()
            return Link(caption=link_caption, uri=link_uri, rel=link_rel)
        times = dd_element.cssselect("time")
        if len(times):
            time_el = times[0]
            return datetime.datetime.strptime(time_el.attrib["datetime"].strip(), "%Y-%m-%d")
    return dd_element.text.strip()


def extract_links(client, base_uri, doc):
    """
    Extract all links of a document as Resources

    :param client: current client
    :param base_uri: bas uri of the document
    :param doc: document to extract from
    :return: dict of Resources (key: rel)
    """
    links = {}
    # first add the embeds
    embeds = extract_embeds(doc, base_uri)
    embed_links = []
    for href, e in embeds.items():
        link = e.cssselect("summary a")[0]
        embed_links.append(link)
        rel = link.attrib["rel"]
        title = link.text.strip()
        link_obj = Resource._parse_embed(client, e, uri=href, rel=rel, title=title)
        if rel in links:
            links[rel].append(link_obj)
        else:
            links[rel] = ResourceList([link_obj])
    for link in doc.cssselect("a"):
        if "rel" in link.attrib and link.attrib["rel"] != "self" and link not in embed_links:
            link_obj = Resource.link(client, get_uri(link.attrib['href'], base_uri), rel=link.attrib["rel"],
                                     title=link.text)
            if link.attrib["rel"] in links:
                links[link.attrib["rel"]].append(link_obj)
            else:
                links[link.attrib["rel"]] = ResourceList([link_obj])
    return links


def strip_doc_for_data(doc, self_uri):
    # copy document -> not affecting original
    strip_doc = doc.__copy__()

    # find all embeds (indicated by rel='self') and get their roots (<article>)
    embeds = extract_embeds(strip_doc, self_uri)
    for e in embeds.values():
        # remove from document
        e.getparent().remove(e)
    return strip_doc


def extract_doc_link(doc, default, base_uri):
    try:
        head_link = doc.cssselect("head link")[0]
        return get_uri(head_link.attrib["href"], base_uri)
    except IndexError:
        return default


def extract_embeds(doc, self_uri):
    """
    Return the Elements of all embedded resource

    :param doc: document to extract from
    :param self_uri: uri of the document
    :return: dict of Elements (Key: uri)
    """
    details = doc.cssselect('details')
    embeds = {}
    for d in details:
        if d == doc:
            continue
        s = d.cssselect("summary")
        if not s:
            continue
        link = s[0].cssselect("a")
        if not link:
            continue
        if link[0].attrib['href'] != self_uri:
            embeds[get_uri(link[0].attrib['href'], self_uri)] = d
    return embeds


def extract_forms(client, doc, self_uri):
    """
    Return all forms in a document not embedded in another resource

    :param client: current client
    :param doc: document/element to extract from
    :param self_uri: URI of the resource to extract from
    :return: all forms found as Form object
    """
    doc.make_links_absolute(self_uri)
    doc = strip_doc_for_data(doc, self_uri)
    forms = {}
    for el in doc.cssselect("form"):
        if 'name' in el.attrib and el.attrib['name']:
            forms[el.attrib['name']] = Form(client, el)
    return forms


class ResourceList(list):
    def traverse(self, rels):
        """
        Find all resources described by a path of relations
        relative to this elements of this list

        :param rels: List of relations as strings
        :return: ResourceList of the resources found
        """
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


class Form(object):
    def __init__(self, client, element):
        self._client = client
        self._doc = element
        self._parse()

    def _parse(self):
        self.name = self._doc.attrib['name'] if 'name' in self._doc.attrib else ''
        self.method = self._doc.attrib['method'].lower() if 'method' in self._doc.attrib else 'get'
        self.action = self._doc.attrib['action'] if 'action' in self._doc.attrib else ''

        self.params = {}
        for tp in ['input', 'textarea', 'select']:
            for elt in self._doc.cssselect(tp):
                if 'type' in elt.attrib and elt.attrib['type'] == 'hidden':
                    continue
                if 'name' in elt.attrib:
                    self.params[elt.attrib['name']] = None

    def submit(self):
        """
        Submit the form by creating a request based on the values stored in
        self.params

        :return: A resource returned by the server
        """
        params = urlencode({key: value for key, value in self.params.items() if value is not None})
        if self.method == 'get':
            up = urlparse(self.action)
            if up.params:
                allparams = "%s&%s" % (up.params, params)
            else:
                allparams = params
            where = urlunparse((up.scheme, up.netloc, up.path,
                                up.params, allparams, ''))
            return Resource.from_uri(self._client, where)
        else:
            ret_html = request.urlopen(self.action, params).read()
            return Resource.from_html(self._client, html_str=ret_html)


class Client(object):
    """
    Represents the root of all resources

    Contains functionality to cache Resource objects by URI, to avoid
    having multiple Resources pointing to the same URI
    """
    def __init__(self, root_url="", root_html_str="", root=None):
        self._root = root
        self._resources_list = []
        if root is None:
            if root_url:
                self._root = Resource.from_uri(self, root_url)
            elif root_html_str:
                self._root = Resource.from_html(self, html_str=root_html_str)
        if self._root is not None:
            self._resources_list.append(self._root)

    @property
    def _resources(self):
        res_dict = {}
        for res in self._resources_list:
            res_dict[res.uri] = res
        return res_dict

    def traverse(self, rels):
        """
        Get the resources described by a path of relations
        relative to this clients root

        :param rels: List of relations as strings
        :return: ResourceList of the resources found
        """
        return self._root.traverse(rels)

    def get_resource(self, uri, fetch=False):
        if uri in self._resources:
            if fetch:
                self._resources[uri].fetch()
            return self._resources[uri]
        raise KeyError(uri)

    def add_resource(self, res):
        self._resources_list.append(res)

    @staticmethod
    def from_url(url):
        return Client(root_url=url)

    @staticmethod
    def from_html(html_str):
        return Client(root_html_str=html_str)

    @staticmethod
    def from_resource(resource):
        return Client(root=resource)
