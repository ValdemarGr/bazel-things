#!/bin/bash
LOOK=${BASH_SOURCE[0]}.runfiles

RUNFILES=$(find $LOOK -name "write_bloop_config.py" | head -n 1)

DEPS=$(cd $4 && bazel query "deps(//$1:all)" --output location | grep -E '.\.jar$' | grep maven | sed 's/BUILD:[0-9]*:[0-9]*: source file @maven\/\/://')

echo $DEPS | python3 $RUNFILES --name $1 --path $(pwd) --home $HOME --ver $2 > $3
