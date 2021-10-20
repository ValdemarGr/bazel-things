#!/usr/bin/env python3
import argparse
import json
import sys
import subprocess
import os
import re

whitelist = [
        "cats",
        "typelevel",
        "http4s",
        "fs2",
        "tpolecat",
        "circe",
        "shapeless",
        "comcast"
]
def whitelisted(x):
    for w in whitelist:
        if w in x:
            return True
    return False

def get_maven_deps():
    lines = subprocess.Popen(["bash", "-c", "bazel query \"@maven//:all\""], stdout=subprocess.PIPE).stdout.readlines()
    formatted = [x.decode("utf-8").strip() for x in lines]
    print(f"queried {len(formatted)} maven deps from bazel", file=sys.stderr)
    return formatted

def get_scala_projects():
    lines = subprocess.Popen(["bash", "-c", "bazel query \"deps(...)\" | rg scala_project | sed 's/\/.*$//g' | uniq"], stdout=subprocess.PIPE).stdout.readlines()
    formatted = [x.decode("utf-8").strip() for x in lines]
    print(f"queried {len(formatted)} maven deps from bazel", file=sys.stderr)
    return formatted

def get_deps_tree_for(project):
    lines = subprocess.Popen(["bash", "-c", f"bazel query \"{project}//src/main/...\""], stdout=subprocess.PIPE).stdout.readlines()
    formatted = [x.decode("utf-8").strip() for x in lines]
    print(f"queried {len(formatted)} maven deps from bazel", file=sys.stderr)
    return formatted

maven_deps = [x for x in get_maven_deps() if whitelisted(x)]
scala_projects = get_scala_projects()
all_inhouse_deps = [d for proj in scala_projects for d in get_deps_tree_for(proj)]

combined = [x for x in all_inhouse_deps + maven_deps if not x.endswith("extension") and not x.endswith("outdated")]
filted = [f"\"{x}\"" for x in combined if not re.search("\d+_\d+_\d+", x)]

print(",\n".join(filted))
