load("@io_bazel_rules_scala//scala:scala.bzl", "scala_junit_test")

# https://github.com/bazelbuild/rules_scala/blob/master/scala/private/rules/scala_test.bzl#L123-L146
def scala_junit_suite(
    name,
    srcs = [],
    visibility = None,
    tags = [],
    **kwargs):
  ts = []
  for test_file in srcs:
    new_name = name + "_suite_" + test_file.split(".")[0]
    scala_junit_test(
        name = new_name,
        srcs = [test_file],
        visibility = visibility,
        unused_dependency_checker_mode = "off",
        tags = tags,
        **kwargs
    )
    ts.append(new_name)

  native.test_suite(name = name, tests = ts, visibility = visibility, tags = tags)
