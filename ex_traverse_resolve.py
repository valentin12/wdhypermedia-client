#!/usr/bin/python3
from wdhypermedia import Resource

res = Resource.parse("file:///home/valentin/Programmierung/innoQ/wdhypermedia-client/html/projects.html")
projects = res.traverse("http://rels.innoq.com/project")
project = projects[0].resolve()
print(project.traverse("http://rels.innoq.com/customer")[0].resolve().__dict__)  # customer __dict__
