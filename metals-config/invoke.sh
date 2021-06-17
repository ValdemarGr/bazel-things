#!/bin/bash
LOOK=${BASH_SOURCE[0]}.runfiles

RUNFILES=$(find $LOOK -name "write_bloop_config.py" | head -n 1)
COURSIER=$(coursier fetch -q org.scala-lang:scala-compiler:$2)

DEPS=$(cd $4 && bazel query "deps(//$1:all)" --output location | grep -E '.\.jar$' | grep maven | sed 's/BUILD:[0-9]*:[0-9]*: source file @maven\/\/://')

echo $DEPS | python3 $RUNFILES --name $1 --path $4 --home $HOME --ver $2 --compiler "$COURSIER" > $3
