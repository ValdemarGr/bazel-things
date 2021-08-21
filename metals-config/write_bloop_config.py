#!/usr/bin/env python3
import argparse
import json
import sys
import subprocess
import os

parser = argparse.ArgumentParser()
parser.add_argument("--name", type=str)

args = parser.parse_args()
path = os.getcwd()

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
rec_paths = list(set(scala_paths("scala_project_")))
asLst = list(maven_deps)

absPath = path + "/" + args.name

version = [x for x in bazel_deps if "scala-library" in x][0].split(":")[2]
only_comp = fetch_deps([f"org.scala-lang:scala-compiler:{version}"], with_sources=False)
comp = [x for x in only_comp if "scala" in x]
print(f"using compiler items {comp}", file=sys.stderr)

sources = list(filter(lambda x: x.endswith("sources.jar"), asLst))
nonSources = list(filter(lambda x: not x.endswith("sources.jar"), asLst))

plugins = set(["kind-projector"])

def modularize(dep):
    toSearch = "maven2/"
    strippedStr = dep[dep.find(toSearch)+len(toSearch):]
    removedJar = strippedStr[:strippedStr.rfind("/")]
    ver = removedJar[removedJar.rfind("/") + 1:]
    rest = removedJar[:removedJar.rfind("/")]
    pkgName = rest[rest.rfind("/") + 1:]
    org = rest[:rest.rfind("/")].replace("/", ".")

    return {
            "organization": org,
            "name": pkgName,
            "version": ver,
            "configurations": "default",
            "artifacts": [
                {
                    "name": pkgName,
                    "path": dep
                },
                {
                    "name": pkgName,
                    "classifier": "sources",
                    "path": dep[:-4] + "-sources.jar"
                }
            ]
    }

def first_or(s, d):
    return next((l for l in nonSources if s in l and False), d)

found_plugins = [x for x in nonSources for p in plugins if p in x]

                              
out = {
    "version": "1.4.0",
    "project": {
        "name" : args.name,
        "scala": {
            "organization": "org.scala-lang",
            "name": "scala-compiler",
            "version": version,
            "options":[
                f"-Xplugin:{p}" for p in found_plugins
                ],
            "jars": comp
        },
        "directory" : absPath,
        "workspaceDir" : path,
        "sources" : [
            absPath + "/src/main/scala",
            absPath + "/main/scala",
            absPath + "/src/test/scala",
            absPath + "/test/scala"
        ] + [x + "/src/main/scala" for x in rec_paths] + [x + "/src/test/scala" for x in rec_paths],
        "dependencies":[],
        "classpath": nonSources + list(filter(lambda x: "scala-library" in x, comp)),
        "out": path + "/.bloop/" + args.name,
        "classesDir": path + "/.bloop/" + args.name + "/scala-" + ".".join(version.split(".")[:-1]) + "/classes",
        "resolution": {
            "modules": list(map(lambda x: modularize(x), nonSources)) 
        },
        "tags": ["library"]
    }
}

print(json.dumps(out, indent=4, sort_keys=True))
