#!/usr/bin/python3
from wdhypermedia import Ressource
res = Ressource.parse("file:///home/valentin/Programmierung/innoQ/wdhypermedia-client/html/projects.html")
project = res.traverse("http://rels.innoq.com/project")[0]
print(project.traverse("http://rels.innoq.com/customer")[0].resolve().__dict__)  # customer __dict__