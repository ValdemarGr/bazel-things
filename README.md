# Bazel things
## Dependencies
This is a wrapper for maven dependencies which just exposes depesdencies in a sbtish way.
Scala version numbers are automatically appended to dependencies which supports binding dependencies late.
This allows modular dependency declarations.
### Usage
In your `WORKSPACE` or some dependency file import the rules via `http_archive`.
```starlark
http_archive(
    name = "scala_things",
    sha256 = "zipSha",
    strip_prefix = "bazel-things%s" % commitSha,
    url = "https://github.com/valdemargr/bazel-things/archive/%s.zip" % commitSha,
)

load("@scala_things//dependencies:init.bzl", "bazel_things_dependencies")
bazel_things_dependencies()
```
Then dependencies can be declared anywhere as follows.
```starlark
load("@scala_things//dependencies:dependencies.bzl", "java_dependency", "scala_dependency", "scala_fullver_dependency")

some_dependencies = [
  scala_dependency("org.typelevel", "cats-effect", "3.0.1"),
  scala_fullver_dependency("org.typelevel", "kind-projector", "0.11.3"),
  java_dependency("org.apache.poi", "poi", "4.1.2")
]
```
At some point the effectful installation must be invoked.
```starlark
load("@scala_things//dependencies:dependencies.bzl", "install_dependencies", "make_scala_versions")

scala_versions = make_scala_versions("2", "12", "10")
install_dependencies(some_dependencies, scala_versions)
```
