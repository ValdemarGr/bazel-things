#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys
import subprocess
import os
import re
from functools import reduce

def bold(msg):
    return '\033[1m' + msg + '\033[0m'

def yellow(msg):
    return '\033[94m' + msg + '\033[0m'

def red(msg):
    return '\033[91m' + msg + '\033[0m'

def green(msg):
    return '\033[92m' + msg + '\033[0m'

def prefix(msg):
    return 'bloop import: ' + msg

def alert(msg):
    print(yellow(prefix(msg)) + '\033[0m', file=sys.stderr)

def stop(msg):
    print(red(bold(prefix(msg))) + '\033[0m', file=sys.stderr)
    exit(-1)

parser = argparse.ArgumentParser()
parser.add_argument("--name", type=str)
parser.add_argument("--path", type=str)

parser.add_argument("--flags", dest='flags', action='store_true')
parser.add_argument("--no-flags", dest='flags', action='store_false')
parser.set_defaults(flags=False)

parser.add_argument("--compiler-version", dest='compiler_version', type=str)
parser.set_defaults(compiler_version=None)

parser.add_argument("--gen-path", dest='gen_path', nargs='+', help='Extra paths to search for jars (bazel-bin/<intput>)')
parser.set_defaults(gen_path=[])

args = parser.parse_args()
path = os.getcwd()

# maven dependencies start
def fetch_everything():
    # read to block so it doesn't race
    cmd1 = """bazel build @maven//... --ui_event_filters=-debug"""
    cmd1_fmt = green(bold(f"""'{cmd1}'"""))
    alert(f"getting all maven items; running command {cmd1_fmt}")
    subprocess.Popen(["bash", "-c", cmd1], stdout=subprocess.PIPE).stdout.readlines()

    cmd2 = """bazel build //... --ui_event_filters=-debug"""
    cmd2_fmt = green(bold(f"""'{cmd2}'"""))
    alert(f"building everything I can; running command {cmd2_fmt}")
    subprocess.Popen(["bash", "-c", cmd2], stdout=subprocess.PIPE).stdout.readlines()

def get_all_maven_jars():
    cmd = """bazel aquery --ui_event_filters=-debug 'outputs(".*\.jar", @maven//:all)' | rg Outputs | awk ' { print $2 } ' | sed 's/[][]//g' | xargs -I{} echo $(pwd)/{}"""
    cmd_fmt = green(bold(f"""'{cmd}'"""))
    alert(f"getting all maven dependencies; running command {cmd_fmt}")
    lines = subprocess.Popen(["bash", "-c", cmd], stdout=subprocess.PIPE).stdout.readlines()
    formatted = [x.decode("utf-8").strip() for x in lines]
    return set(formatted)

def partition_jars_with_sources(jars_set):
    regex = """^.*\/(.*$)"""
    matched = [(m, re.match(regex, m).group(1)) for m in jars_set]
    filted = [(x, name) for (x, name) in matched if name is not None and not name.startswith("header_")]
    sources = [(x, name.replace("-sources.jar", "")) for (x, name) in filted if name.endswith("-sources.jar")]
    jars = [(x, name.replace(".jar", "")) for (x, name) in filted if not name.endswith("-sources.jar")]

    return (jars, sources)

def correlate_jars(jars, sources):
    source_map = { name: path for (path, name) in sources }

    return { name: { "path": path, "source_path": source_map.get(name) } for (path, name) in jars }

alert(f"beginning import of maven dependencies")
alert(f"making sure that bazel has fetched everything")
fetch_everything()
alert(f"querying for the output jars and source jars for the maven rule")
md = get_all_maven_jars()
(jars, sources) = partition_jars_with_sources(md)
alert(f"found {len(jars)} binary jars and {len(sources)} source jars")
correlated_deps = correlate_jars(jars, sources)
alert(f"using {len(correlated_deps)} unique dependencies")
# maven dependencies end

# imported code start
def all_dirs_with_scala_code(base_path):
    all_files_for_path = list(base_path.glob('**/*.scala'))
    all_interesting_dirs = [d.resolve().parent for d in all_files_for_path]
    return all_interesting_dirs

def get_magic_projects(magic_string):
    cmd = f"""bazel query --ui_event_filters=-debug //external:all | sed 's/\/\/external://g' | grep {magic_string}"""
    cmd_fmt = green(bold(f"""'{cmd}'"""))
    alert(f"getting all projects in external; running command {cmd_fmt}")
    lines = subprocess.Popen(["bash", "-c", cmd], stdout=subprocess.PIPE).stdout.readlines()
    formatted = [x.decode("utf-8").strip() for x in lines]

    dirname = Path(".").resolve().name
    external_dir = Path(f"./bazel-{dirname}/external").resolve()
    external_paths = [Path(external_dir / d) for d in formatted]

    return (formatted, external_paths)

def get_imported_code(external_paths):
    flat_paths = [z for x in external_paths for z in all_dirs_with_scala_code(x)]

    prepped = list(sorted([str(x) for x in flat_paths]))

    eliminated = []
    prev = None
    for x in prepped:
        # if x is a prefix of s then the path s must include x, thus x can be eliminated
        if prev is not None and prev.startswith(x):
            continue
        else:
            # reset the comparison to x, since x is on a distinct path from s
            prev = x
            eliminated.append(x)

    return eliminated
    

magic_string = "scala_project_"
alert(f"importing projects that contain the magic string '{magic_string}'")
(fmt, ep) = get_magic_projects(magic_string)
alert(f"found magic projects: {fmt}")
imported_dirs = get_imported_code(ep)
alert(f"imported {len(imported_dirs)} directories from {len(fmt)} projects")
# imported code end

# flags begin
flags = []
alert(f"using flags compiler?: {args.flags}")
if args.flags:
    d = Path(__file__).resolve().parent.parent
    alert(f"found flags file at {str(d)}")
    import imp
    flagsModule = imp.load_source('flags', str((d / 'flags' / 'flags.bzl').resolve()))
    flags = flagsModule.flags
    alert(f"using flags {flags}")
# flags end

# generated code start
scanned_jars = []
scanned_src_jars = []
p = Path('./bazel-bin')
d = p.is_dir()
alert(f"found bazel-bin at {str(p.resolve())}? {d}")
if p.is_dir():
    # everything else than external is interesting
    d = p
    all_jars = [str(x.resolve()) for k in args.gen_path for x in list((p / k).glob('**/*.jar')) if d != x]
    alert(f"found {len(all_jars)} generated jars")

    scanned_src_jars = [x for x in all_jars if x.endswith("src.jar")]
    scanned_jars = [x for x in all_jars if not x.endswith("src.jar")]
    alert(f"{scanned_src_jars} were source jars")
    alert(f"{scanned_jars} were binary jars")
# generated code end

# compiler version start
alert(f"has compiler version? {args.compiler_version is not None}")
def get_scala_version():
    cmd = """bazel query @maven//:all | grep org_scala_lang_scala_library | grep -Po "\d+_\d+_\d+" | sed 's/_/./g' | head -n 1"""
    cmd_fmt = green(bold(f"""'{cmd}'"""))
    alert(f"attempting to find compiler version via the org_scala_lang_scala_library dependency; running command {cmd_fmt}")
    lines = subprocess.Popen(["bash", "-c", cmd], stdout=subprocess.PIPE).stdout.readlines()
    formatted = [x.decode("utf-8").strip() for x in lines]

    return list(set(formatted))

compiler_version = args.compiler_version
if compiler_version is None:
    alert(f"guessing compiler version")
    guesses = get_scala_version()
    alert(f"guesses: {guesses}")
    if len(guesses) == 0:
        stop(f"could not guess compiler version, quitting")
    compiler_version = guesses[0]
    alert(f"using compiler version {compiler_version}")
# compiler version end

# generate dependency json start
def make_artifact(org, pkgName, version, artifacts):
    return {
            "organization": org,
            "name": pkgName,
            "version": version,
            "configurations": "default",
            "artifacts": artifacts
    }

def make_artifact_with_source(name, binary_path, source_path=None):
    maybe_source =  [{
        "name": name,
        "classifier": "sources",
        "path": source_path
    }] if source_path is not None else []

    return make_artifact(name, name, "unknown", [
        {
            "name": name,
            "path": binary_path
        }
    ] + maybe_source)

def make_maven_artifacts(correlated_deps):
    return [make_artifact_with_source(name, pathinfo["path"], pathinfo["source_path"]) for (name, pathinfo) in correlated_deps.items()]

def make_scanned(scanned_jars, scanned_src_jars):
    comp = [{"name": f"scanned_{str(i)}", "path": j} for (i, j) in enumerate(scanned_jars)]
    srcs = [{"name": f"scanned_{str(len(comp) + i)}", "path": j, "classifier": "sources"} for (i, j) in enumerate(scanned_src_jars)]
    return make_artifact("scanned_jars", "scanned_jars", "1.0.0", comp + srcs)

alert(f"generating maven dependency json")
mvn_artifacts = make_maven_artifacts(correlated_deps)
alert(f"generated {len(mvn_artifacts)} maven dependencies")
alert(f"generating generated code dependency json")
scanned_artifact = make_scanned(scanned_jars, scanned_src_jars)
l = len(scanned_artifact["artifacts"])
alert(f"generated {l} codegen dependencies")
scanned_artifacts = [scanned_artifact] if l > 0 else []

all_artifacts = mvn_artifacts + scanned_artifacts
alert(f"total of {len(all_artifacts)} artifacts")
# generate dependency json end

exit(0)

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
