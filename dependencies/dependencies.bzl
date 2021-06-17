load("@rules_jvm_external//:defs.bzl", "maven_install")
load("@rules_jvm_external//:specs.bzl", "maven", "parse")
load("@bazel_skylib//lib:partial.bzl", "partial")

def to_string_version(scala_versions):
    return scala_versions["major"] + "." + scala_versions["minor"] + "." + scala_versions["patch"]

def apply_scala_version(scala_versions, s):
    return s + "_" + scala_versions["major"] + "_" + scala_versions["minor"]

def _java_to_maven(group, name, version):
    art = parse.parse_maven_coordinate(group + ":" + name + ":" + version)
    return maven.artifact(
        group =  art['group'],
        artifact = art['artifact'],
        packaging =  art.get('packaging'),
        classifier = art.get('classifier'),
        version =  art['version'],
        exclusions = None,
    )

_scala_dependency_tag = "scala_dependency"
_scala_fullver_dependency_tag = "scala_fullver_dependency"
_java_dependency_tag = "java_dependency"

def _normalize_version(dep, scala_versions):
  if (_scala_dependency_tag == dep["tag"]):
    return dep["version"] + "_" + scala_versions["major"] + "." + scala_versions["minor"]
  elif (_scala_fullver_dependency_tag == dep["tag"]):
    return dep["version"] + "_" + scala_versions["major"] + "." + scala_versions["minor"] + "." + scala_versions["patch"]
  else:
    return dep["version"]

def _dep_to_java(dep, scala_versions):
  return _java_to_maven(dep["group"], dep["name"], _normalize_version(dep, scala_versions))

def java_dependency(group, name, version):
  return {
      "tag": _java_dependency_tag,
      "group": group,
      "name": name,
      "version": version
  }

def scala_dependency(group, name, version):
  j = java_dependency(group, name, version)
  j["tag"] = _scala_dependency_tag
  return j

def scala_fullver_dependency(group, name, version):
  j = java_dependency(group, name, version)
  j["tag"] = _scala_fullver_dependency_tag
  return j

def make_scala_versions(major, minor, patch):
  return {
      "major": major,
      "minor": minor,
      "patch": patch
  }

def install_dependencies(deps, scala_versions):
    as_mvn = [_dep_to_java(d, scala_versions) for d in deps]
    maven_install(
        artifacts = as_mvn,
        repositories = [
            "https://repo.maven.apache.org/maven2/",
            "https://mvnrepository.com/artifact",
            "https://maven-central.storage.googleapis.com",
        ],
        fetch_sources = True,
        generate_compat_repositories = True,
        #        maven_install_json = "//:maven_install.json",
    )
