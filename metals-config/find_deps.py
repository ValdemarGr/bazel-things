import os

def go(path):
  scala_stream = os.popen(f'bazel query "deps(...)" --output location | rg "/[^ ]+scala_project_[^/]+" -o | uniq')
  scala_ouput = scala_stream.readlines()
  
  dep_stream = os.popen(f"""cd ${path} && bazel query "deps(...)" --output location | grep -E '.\.jar$' | grep maven | sed 's/BUILD:[0-9]*:[0-9]*: source file @maven\/\/://'""")
  dep_output = dep_stream.readlines()
  
  nexts = [dep for dep in go(next) for next in scala_output]
                        
  return nexts + dep_output
                        
