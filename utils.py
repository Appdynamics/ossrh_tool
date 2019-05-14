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
