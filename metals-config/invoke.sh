#!/bin/bash
RUNFILES=${BASH_SOURCE[0]}.runfiles/__main__/metals-config

DEPS=$(cd $4 && bazel query "deps(//$1:all)" --output location | grep -E '.\.jar$' | grep maven | sed 's/BUILD:[0-9]*:[0-9]*: source file @maven\/\/://')

echo $DEPS | python3 $RUNFILES/write_bloop_config.py --name $1 --path $(pwd) --home $HOME --ver $2 > $3
