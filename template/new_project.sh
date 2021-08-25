#!/bin/bash
die () {
    echo >&2 "$@"
    exit 1 
}
REQUIRED=4
[ "$#" -eq $REQUIRED ] || die "$REQUIRED argument (name, major, minor, patch) required, $# provided"

NAME=$1
MAJOR=$2
MINOR=$3
PATCH=$4

NEWEST_HASH=$(git ls-remote git@github.com:casehubdk/bazel-things HEAD | awk ' { print $1 } ')
NEWEST_SHA=$(curl https://github.com/valdemargr/bazel-things/archive/$(git ls-remote git@github.com:casehubdk/bazel-things HEAD | awk ' { print $1 } ')/.zip -L | sha256sum | awk ' { print $1 } ')

mkdir -p src/main/scala
cat << EOF > src/BUILD.bazel
load("@io_bazel_rules_scala//scala:scala.bzl", "scala_binary")

scala_binary(
    name = "bin",
    main_class = "your_project.Main",
    # deps = ["//src/main/scala/your_project"],
)
EOF

echo "3.5.0" > .bazelversion
touch BUILD.bazel

cat << EOF > .bazelrc
build --strategy=Scalac=worker
build --worker_sandboxing
build --google_default_credentials
build --remote_cache=https://storage.googleapis.com/casehub-bazel-build-cache
build --disk_cache=~/.cache/bazelcache

build --host_javabase=@bazel_tools//tools/jdk:remote_jdk11 
build --javabase=@bazel_tools//tools/jdk:remote_jdk11
test --host_javabase=@bazel_tools//tools/jdk:remote_jdk11 
test --javabase=@bazel_tools//tools/jdk:remote_jdk11
EOF

cat << EOF > .scalafmt.conf
version = "2.7.5"
align = most
align.openParenCallSite = true
align.openParenDefnSite = true
maxColumn = 120
continuationIndent.defnSite = 2
assumeStandardLibraryStripMargin = true
danglingParentheses = true
rewrite.rules = [SortImports, RedundantBraces, RedundantParens, SortModifiers]
docstrings = JavaDoc
lineEndings=preserve
newlines.afterCurlyLambda = preserve
EOF

cat << EOF > dependencies.bzl
load("@scala_things//:dependencies/dependencies.bzl", "java_dependency", "scala_dependency", "scala_fullver_dependency", "make_scala_versions", "apply_scala_fullver_version")

scala_versions = make_scala_versions(
    "$MAJOR",
    "$MINOR",
    "$PATCH",
)

project_deps = [
    scala_dependency("org.typelevel", "cats-effect", "3.2.2"),
]

def add_scala_fullver(s):
    return apply_scala_fullver_version(scala_versions, s)
EOF

cat << EOF > WORKSPACE
workspace(name = "$NAME")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

skylib_version = "1.0.3"

http_archive(
    name = "bazel_skylib",
    sha256 = "1c531376ac7e5a180e0237938a2536de0c54d93f5c278634818e0efc952dd56c",
    type = "tar.gz",
    url = "https://mirror.bazel.build/github.com/bazelbuild/bazel-skylib/releases/download/{}/bazel-skylib-{}.tar.gz".format(skylib_version, skylib_version),
)

http_archive(
    name = "rules_proto",
    sha256 = "8e7d59a5b12b233be5652e3d29f42fba01c7cbab09f6b3a8d0a57ed6d1e9a0da",
    strip_prefix = "rules_proto-7e4afce6fe62dbff0a4a03450143146f9f2d7488",
    urls = [
        "https://mirror.bazel.build/github.com/bazelbuild/rules_proto/archive/7e4afce6fe62dbff0a4a03450143146f9f2d7488.tar.gz",
        "https://github.com/bazelbuild/rules_proto/archive/7e4afce6fe62dbff0a4a03450143146f9f2d7488.tar.gz",
    ],
)

load("@rules_proto//proto:repositories.bzl", "rules_proto_dependencies", "rules_proto_toolchains")

rules_proto_dependencies()

rules_proto_toolchains()

# dependencies
# local_repository(
#     name = "scala_things",
#     path = "../bazel-things",
# )
commit_sha = "$NEWEST_HASH"
http_archive(
    name = "scala_things",
    sha256 = "$NEWEST_SHA",
    strip_prefix = "bazel-things-%s" % commit_sha,
    url = "https://github.com/valdemargr/bazel-things/archive/%s.zip" % commit_sha,
)

load("@scala_things//:dependencies/init.bzl", "bazel_things_dependencies")

bazel_things_dependencies()

load("//:dependencies.bzl", "project_deps", "scala_versions")
load("@scala_things//:dependencies/dependencies.bzl", "install_dependencies", "to_string_version")

install_dependencies(project_deps, scala_versions, use_pinned=False) #rem me
#phase2 install_dependencies(project_deps, scala_versions, use_pinned=True)
#phase2 load("@maven//:defs.bzl", "pinned_maven_install")
#phase2 pinned_maven_install()

# scala
rules_scala_version = "b85d1225d0ddc9c376963eb0be86d9d546f25a4a"  # update this as needed
http_archive(
    name = "io_bazel_rules_scala",
    sha256 = "f6fa4897545e8a93781ad8936d5a59e90e2102918e8997a9dab3dc5c5ce2e09e",
    strip_prefix = "rules_scala-%s" % rules_scala_version,
    type = "zip",
    url = "https://github.com/bazelbuild/rules_scala/archive/%s.zip" % rules_scala_version,
)

load("@io_bazel_rules_scala//:scala_config.bzl", "scala_config")
load("//:dependencies.bzl", "scala_versions")

scala_config(to_string_version(scala_versions))

load("@io_bazel_rules_scala//scala:scala.bzl", "scala_repositories")

register_toolchains("@scala_things//toolchain")

scala_repositories()

load("@io_bazel_rules_scala//testing:junit.bzl", "junit_repositories", "junit_toolchain")

junit_repositories()

junit_toolchain()
EOF

bazel run @maven//:pin
sed -i 's/.*#rem me//' WORKSPACE
sed -i 's/#phase2 //' WORKSPACE
bazel run @unpinned_maven//:pin
