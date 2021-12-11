#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys
import subprocess
import os

parser = argparse.ArgumentParser()
parser.add_argument("--name", type=str)
parser.add_argument("--path", type=str)

parser.add_argument("--flags", dest='flags', action='store_true')
parser.add_argument("--no-flags", dest='flags', action='store_false')
parser.set_defaults(flags=False)

parser.add_argument("--extra-paths", dest='extra_paths', nargs='+', help='Extra paths to search for jars (bazel-bin/<intput>)')
parser.set_defaults(extra_paths=[])

args = parser.parse_args()
path = os.getcwd()

flags = []
if args.flags:
    d = Path(__file__).resolve().parent.parent
    import imp
    flagsModule = imp.load_source('flags', str((d / 'flags' / 'flags.bzl').resolve()))
    flags = flagsModule.flags

# scan for generated code
scanned_jars = []
scanned_src_jars = []
p = Path('./bazel-bin')
if p.is_dir():
    # everything else than external is interesting
    d = p
    all_jars = [str(x.resolve()) for k in args.extra_paths for x in list((p / k).glob('**/*.jar')) if d != x]

    scanned_src_jars = [x for x in all_jars if x.endswith("src.jar")]
    scanned_jars = [x for x in all_jars if not x.endswith("src.jar")]

def query_bazel_maven_deps():
    lines = subprocess.Popen(["bash", "-c", "bazel query \"@maven//:all\" --output=build | grep maven_coordinates | sed 's/.*tes=//' | sed 's/\"].*//'"], stdout=subprocess.PIPE).stdout.readlines()
    formatted = [x.decode("utf-8").strip() for x in lines]
    print(f"queried {len(formatted)} deps from bazel", file=sys.stderr)
    return formatted

def fetch_deps(maven_strings, with_sources=True):
    e = ""
    if with_sources:
        e = f"--sources"
    sane_strings = " ".join(maven_strings)
    lines = subprocess.Popen(["bash", "-c", f"coursier fetch --default=true {e} {sane_strings}"], stdout=subprocess.PIPE).stdout.readlines()
    formatted = [x.decode("utf-8").strip() for x in lines]
    print(f"found {len(formatted)} jar + source items", file=sys.stderr)
    return formatted

def scala_paths(magic_string):
    lines = subprocess.Popen(["bash", "-c", f"""cd {path} && bazel query "deps(...)" --output location | rg "/[^ ]+{magic_string}[^/]+" -o | uniq"""], cwd=path, stdout=subprocess.PIPE).stdout.readlines()
    scala_output = [x.decode("utf-8").strip() for x in lines if x.decode("utf-8").strip() != path]
    #dont recurse, that doesnt make sense. All deps are declared locally
    #return scala_output + [x for next in scala_output for x in scala_paths(next)]
    return scala_output

bazel_deps = query_bazel_maven_deps()
maven_deps = fetch_deps(bazel_deps)

import re
def maybe_include(x):
    if re.search("std", x) is not None:
        return [x + "/src/main/scala", x + "/src/test/scala"]
    else:
        prefix = "/src/main/scala/casehub"
        ds = os.listdir(x + prefix)
        if len(ds) != 1:
            print(f"found not exactly 1 directory in {x + prefix}; found {ds}", file=sys.stderr)
            return []
        else:
            d = ds[0]
            return [x + f"/src/main/scala/casehub/{d}/client"]

rec_paths = [y for x in list(set(scala_paths("scala_project_"))) for y in maybe_include(x)]

asLst = list(maven_deps)

absPath = path + "/" + args.path

version = [x for x in bazel_deps if "scala-library" in x][0].split(":")[2]
only_comp = fetch_deps([f"org.scala-lang:scala-compiler:{version}"], with_sources=False)
comp = [x for x in only_comp if "scala" in x]
print(f"using compiler items {comp}", file=sys.stderr)

sources = list(filter(lambda x: x.endswith("sources.jar"), asLst))
nonSources = list(filter(lambda x: not x.endswith("sources.jar"), asLst))

plugins = set(["kind-projector", "better-monadic-for"])

def make_artifact(org, pkgName, version, artifacts):
    return {
            "organization": org,
            "name": pkgName,
            "version": version,
            "configurations": "default",
            "artifacts": artifacts
    }

def make_scanned():
    comp = [{"name": str(i), "path": j} for (i, j) in enumerate(scanned_jars)]
    srcs = [{"name": str(len(comp) + i), "path": j, "classifier": "sources"} for (i, j) in enumerate(scanned_src_jars)]
    return make_artifact("scanned_jars", "scanned_jars", "1.0.0", comp + srcs)

def modularize(dep):
    toSearch = "maven2/"
    strippedStr = dep[dep.find(toSearch)+len(toSearch):]
    removedJar = strippedStr[:strippedStr.rfind("/")]
    ver = removedJar[removedJar.rfind("/") + 1:]
    rest = removedJar[:removedJar.rfind("/")]
    pkgName = rest[rest.rfind("/") + 1:]
    org = rest[:rest.rfind("/")].replace("/", ".")

    return make_artifact(org, pkgName, version, [
        {
            "name": pkgName,
            "path": dep
        },
        {
            "name": pkgName,
            "classifier": "sources",
            "path": dep[:-4] + "-sources.jar"
        }
    ])

    # return {
    #         "organization": org,
    #         "name": pkgName,
    #         "version": ver,
    #         "configurations": "default",
    #         "artifacts": [
    #             {
    #                 "name": pkgName,
    #                 "path": dep
    #             },
    #             {
    #                 "name": pkgName,
    #                 "classifier": "sources",
    #                 "path": dep[:-4] + "-sources.jar"
    #             }
    #         ]
    # }

def first_or(s, d):
    return next((l for l in nonSources if s in l and False), d)

found_plugins = [x for x in nonSources for p in plugins if p in x]

                              
out = {
    "version": "1.4.11",
    "project": {
        "name" : args.name,
        "scala": {
            "organization": "org.scala-lang",
            "name": "scala-compiler",
            "version": version,
            "options":[
                f"-Xplugin:{p}" for p in found_plugins
            ] + flags,
            "jars": comp
        },
        "directory" : absPath,
        "workspaceDir" : path,
        "sources" : [
            absPath + "/src/main/scala",
            absPath + "/main/scala",
            absPath + "/src/test/scala",
            absPath + "/test/scala"
        ] + rec_paths,
        "dependencies":[],
        "classpath": nonSources + list(filter(lambda x: "scala-library" in x, comp)) + scanned_jars,
        "out": path + "/.bloop/" + args.path,
        "classesDir": path + "/.bloop/" + args.path + "/scala-" + ".".join(version.split(".")[:-1]) + "/classes",
        "resolution": {
            "modules": list(map(lambda x: modularize(x), nonSources)) + [make_scanned()]
        },
        "tags": ["library"]
    }
}

print(json.dumps(out, indent=4, sort_keys=True))
