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

"""
This file shall gather all the network calls into ossrh.
"""

import lxml.etree
import requests,sys
import config
import logger

UPLOADS_PATH="/staging/deploy/maven2/"
STAGING_REPOS_PATH="/staging/profile_repositories"
ACTION_CLOSE_PATH="/staging/bulk/close"
ACTION_DROP_PATH="/staging/bulk/drop"
ACTION_PROMOTE_PATH="/staging/bulk/promote"
INSPECT_PATH="/repositories/"

def _get_base_headers():
  if config.agent != None:
    return { 'User-Agent': config.agent }
  else:
    return { }

def get_staging_repository_descriptors(filter):
  if filter == None:
    filter = ""
  else:
    filter = "[" + filter + "]"

  url = config.baseURL + STAGING_REPOS_PATH
  response = requests.get(url, auth=config.creds, headers=_get_base_headers())
  if response.status_code >= 400:
    raise IOError("Error: " + str(response.status_code) + "\n" + response.text)

  xmlNodes = lxml.etree.XML( response.text ).xpath("./data/stagingProfileRepository" + filter)
  return list(map(lambda node: RepositoryDescriptor(node), xmlNodes))

def _inspect_url(url):
  """Recursively explore a repository's content and logs each leaf found this way."""
  response = requests.get(url, auth=config.creds, headers=_get_base_headers())
  if response.status_code >= 400:
    raise IOError("Error: " + str(response.status_code) + "\n" + response.text)

  root = lxml.etree.XML( response.text )
  for item in root.xpath("./data/content-item"):
    uri=item.find("resourceURI").text
    if item.find("leaf").text == 'true':
      logger.log(uri)
    else:
      _inspect_url(uri)

def inspect(name):
  url = config.baseURL + INSPECT_PATH + name + "/content/"
  _inspect_url(url)

def upload_file(local_path, remote_path):
  """Uploads a file at local_path to remote_path on ossrh"""
  url = config.baseURL + UPLOADS_PATH + remote_path
  logger.log("Uploading " + local_path + " -> " + remote_path + "...", no_NL=True)
  with open(local_path, 'rb') as f:
    response = requests.put(url, data=f, auth=config.creds, headers=_get_base_headers())
    if response.status_code >= 400:
      raise IOError("Error: " + str(response.status_code) + "\n" + response.text)
  logger.log(" [done]")


def _post_no_error(url, payload):
  response = requests.post(url, json=payload, auth=config.creds, headers=_get_base_headers())
  if response.status_code >= 400:
    logger.log("Error: " + str(response.status_code))
    logger.log(response.text)
    raise IOError("Server responded with an error.")

def close_repository(repoId):
  url = config.baseURL + ACTION_CLOSE_PATH
  payload = {
    "data": {
      "description": "closed from cli",
      "stagedRepositoryIds": [ repoId ]
    }
  }
  _post_no_error(url, payload)

def drop_repository(repoId):
  url = config.baseURL + ACTION_DROP_PATH
  payload = {
    "data": {
      "description": "dropped from cli",
      "stagedRepositoryIds": [ repoId ]
    }
  }
  _post_no_error(url, payload)

def release_repository(repoId):
  url = config.baseURL + ACTION_PROMOTE_PATH
  payload = {
    "data": {
      "autoDropAfterRelease": True,
      "description": "released from cli",
      "stagedRepositoryIds": [ repoId ]
    }
  }
  _post_no_error(url, payload)

class RepositoryDescriptor:
  """Wrapper around the xml repository node returned by the ossrh api. Makes using that node less awkward"""

  def __init__(self, node):
    self.name = node.find("repositoryId").text
    self.agent = node.find("userAgent").text
    self.isClosed = node.find("type").text == "closed"
    self.isTransitioning = node.find("transitioning").text == "true"

  def __repr__(self):
    return "(name={}, agent={}, attrs={})".format(self.name, self.agent, self.get_attrs())

  def get_attrs(self):
    attrs = [ ]
    if self.isClosed:
      attrs.append("closed")
    if self.isTransitioning:
      attrs.append("transitioning")
    return attrs
