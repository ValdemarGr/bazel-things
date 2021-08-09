#!/bin/bash
CMDS=$@ 2>&1 > /dev/null | grep "buildozer 'remove"
while IFS= read -r line; do
  eval "$line"
done <<< "$CMDS"
