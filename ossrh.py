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

from time import sleep
import sys
import config
import datetime
import logger

from utils import hash_file_sha1, hash_file_md5
import api

class StagingRepository:
  """Represents a staging repository in ossrh"""

  def __init__(self, name):
    self.name = name

  def close(self):
    api.close_repository(self.name)
    repoNode = self.wait_not_transitioning()
    if repoNode == None or not repoNode.isClosed: # Expect the repo to still be here and to be closed
      raise ValueError("Error: Failed to close repository. For more details, log into oss.sonatype.org and look at repository '" + self.name +
      "'.\n node=" + str(repoNode))
    logger.log("Success.")
    
  
  def drop(self):
    api.drop_repository(self.name)
    repoNode = self.wait_not_transitioning()
    if repoNode != None: # Expect the repo to be gone
      raise ValueError("Error: Failed to drop repository '" + self.name +
      "'.\n node=" + str(repoNode))
    logger.log("Success.")
  
  def release(self):
    api.release_repository(self.name)
    repoNode = self.wait_not_transitioning()
    if repoNode != None: # Expect the repo to be gone
      raise ValueError("Error: Failed to promote repository. For more details, log into oss.sonatype.org and look at repository '" + self.name +
      "'.\n node=" + str(repoNode))
    logger.log("Success.")

  # Waits until the repository is not transitioning anymore, and returns the repository's XML descriptor
  def wait_not_transitioning(self):
    logger.log("Waiting for repo '" + self.name + "' to stop transitioning...", no_NL=True)
    while True:
      repoNodes = repoNodes = api.get_staging_repository_descriptors("repositoryId='" + self.name + "'")
      logger.log('.', no_NL=True) # Show some activity in the console
      if len(repoNodes) == 0 or not repoNodes[0].isTransitioning:
        logger.log("") # Line break after the waiting line
        return repoNodes[0] if len(repoNodes) > 0 else None
      sleep(2)

  def inspect(self):
    """Prints the contents of this repository to stdout"""
    api.inspect(self.name)


def find_all_staging_repositories():
  agentFilter = ("userAgent='" + config.agent + "'") if config.agent != None else ""
  profileFilter = ("profileName='" + config.group + "'") if config.group != None else ""
  filters = list(filter(None, [agentFilter, profileFilter]))
  if len(filters) == 0:
    logger.log("Please specify at least one of '--agent' or '--group'")
    raise ValueError("Not enough parameters")
  return api.get_staging_repository_descriptors(' and '.join(filters))

def upload_artifact(project_dir, project_name, project_version, type, hash):
  artefact = "{}-{}{}".format(project_name, project_version, type)
  local_file = "{}/{}".format(project_dir, artefact)
  group = config.getGroupOrFail()
  remote_file = "/{}/{}/{}/{}".format(group.replace('.', '/'), project_name, project_version, artefact)
  api.upload_file(local_file, remote_file)
  if hash == True:
    hash_file_md5(local_file)
    hash_file_sha1(local_file)
    api.upload_file(local_file + ".md5", remote_file + ".md5")
    api.upload_file(local_file + ".sha1", remote_file + ".sha1")

# Creates and uploads `maven-metadata.xml`. I am not sure whether this is required, but in doubt, let's keep it.
def upload_metadata(project_dir, project_name, project_version):
  group = config.getGroupOrFail()
  local_file = "{}/maven-metadata.xml".format(project_dir)
  with open(local_file, "w") as outFile:
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    outFile.write("""<metadata>
      <groupId>{}</groupId>
      <artifactId>{}</artifactId>
      <versioning>
      <release>{}</release>
      <versions>
      <version>{}</version>
      </versions>
      <lastUpdated>{}</lastUpdated>
      </versioning>
      </metadata>""".format(group, project_name, project_version, project_version, now))
  remote_file = "/{}/{}/maven-metadata.xml".format(group.replace('.', '/'), project_name)
  if hash == True:
    hash_file_md5(local_file)
    hash_file_sha1(local_file)
    api.upload_file(local_file + ".md5", remote_file + ".md5")
    api.upload_file(local_file + ".sha1", remote_file + ".sha1")
