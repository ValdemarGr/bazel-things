flags = [
  "-encoding",
  "UTF-8",
  "-deprecation",
  "feature",
  "-unchecked",
  "-Wunused:implicits",
  "-Wunused:explicits",
  "-Wunused:imports",
  "-Wunused:locals",
  "-Wunused:params",
  "-Wunused:privates",
  "-Wvalue-discard"
]

2_13_flags = [
  "-encoding",
  "UTF-8",
  # "-Vimplicits",
  "-Wdead-code",
  "-Wextra-implicit",
  "-Wunused:explicits",
  "-Wunused:implicits",
  "-Wunused:locals",
  "-Wunused:nowarn",
  "-Wunused:params",
  "-Wunused:patvars",
  "-Wunused:privates",
  "-Wvalue-discard",
  "-Xcheckinit",
  "-Xfatal-warnings",
  "-Xlint:-byname-implicit",
  "-Xlint:adapted-args",
  "-Xlint:doc-detached",
  "-Xlint:inaccessible",
  "-Xlint:infer-any",
  "-Xlint:missing-interpolator",
  "-Xlint:nullary-unit",
  "-Xlint:option-implicit",
  "-Xlint:private-shadow",
  "-Xlint:stars-align",
  "-Xlint:type-parameter-shadow",
  "-Yrangepos",
  "-Ywarn-dead-code",
  "-Ywarn-numeric-widen",
  "-Ywarn-unused",
  "-Ywarn-unused:imports",
  "-Ywarn-value-discard",
  "-Ywarn-macros:after",
  "-Ymacro-annotations",
  "-deprecation",
  "-explaintypes",
  "-feature",
  "-language:existentials",
  "-language:higherKinds",
  "-language:implicitConversions",
  "-unchecked",
  # "-Vtype-diffs",
  # "-Xlint:strict-unsealed-patmat", 
]

def unused_targets_ignored(scala_version):
  http4s_uri_macro = [
    "@maven//:org_typelevel_literally_" + scala_version,
    "@maven//:org_typelevel_cats_parse_" + scala_version,
    "@maven//:com_comcast_ip4s_core_" + scala_version,
    "@maven//:org_typelevel_case_insensitive_" + scala_version,
    "@maven//:org_http4s_http4s_dsl_" + scala_version,
    "@maven//:org_typelevel_cats_kernel_" + scala_version,
    "@maven//:co_fs2_fs2_core_" + scala_version,
  ]
  
  jakarta_mail = [
    "@maven//:javax_mail_mail"
  ]
  
  all = http4s_uri_macro + jakarta_mail
    
  return {
    "all": all,
    "http4s_uri_macro": http4s_uri_macro,
    "jakarta_mail": jakarta_mail
  }
