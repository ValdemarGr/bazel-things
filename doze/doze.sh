#!/bin/bash
echo "running $@"
CMDS=$(eval $@ 2>&1 > /dev/null | grep "buildozer 'remove")
while IFS= read -r line; do
  eval "$line"
  echo "evalling ${line/_2_[0-9]*/""}"
done <<< "$CMDS"
