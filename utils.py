# Copyright 2019 AppDynamics, Inc., and its affiliates
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import hashlib

def hash_file_md5(local_file):
  hasher = hashlib.md5()
  with open(local_file, "rb") as inFile:
    buf = inFile.read()
    hasher.update(buf)
  with open(local_file + ".md5", "w") as outFile:
    outFile.write(hasher.hexdigest())

def hash_file_sha1(local_file):
  hasher = hashlib.sha1()
  with open(local_file, "rb") as inFile:
    buf = inFile.read()
    hasher.update(buf)
  with open(local_file + ".sha1", "w") as outFile:
    outFile.write(hasher.hexdigest())
