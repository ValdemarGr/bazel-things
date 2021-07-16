import argparse
import json
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--name", type=str)
parser.add_argument("--path", type=str)
parser.add_argument("--home", type=str)
parser.add_argument("--ver", type=str)
parser.add_argument("--compiler", type=str)

args = parser.parse_args()

deps = sys.stdin.read()

asLst = deps.split()

absPath = args.path + "/" + args.name

comp = args.compiler

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

def mk_def(l):
    s = args.home + "/.sbt/boot/scala-" + args.ver + "/lib/" + l + ".jar"
    return first_or(l, s)

found_plugins = [x for x in nonSources for p in plugins if p in x]
defas = [
    mk_def("scala-reflect"),
    mk_def("scala-compiler"),
    mk_def("scala-library"),
]

out = {
    "version": "1.4.0",
    "project": {
        "name" : args.name,
        "scala": {
            "organization": "org.scala-lang",
            "name": "scala-compiler",
            "version": args.ver,
            "options":[
                f"-Xplugin:{p}" for p in found_plugins
                ],
            "jars": comp.split()
        },
        "directory" : absPath,
        "workspaceDir" : args.path,
        "sources" : [
            absPath + "/src/main/scala",
            absPath + "/main/scala"
        ],
        "dependencies":[],
        "classpath": nonSources,
        "out": args.path + "/.bloop/" + args.name,
        "classesDir": args.path + "/.bloop/" + args.name + "/scala-" + ".".join(args.ver.split(".")[:-1]) + "/classes",
        "resolution": {
            "modules": list(map(lambda x: modularize(x), nonSources)) 
        },
        "tags": ["library"]
    }
}

print(json.dumps(out))
