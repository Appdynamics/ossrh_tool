import logger

# OSSRH credentials
creds = None
# Per-build isolation id
agent = None
# Artifact group
group = None
# OSSRH base URL
baseURL = "https://oss.sonatype.org/service/local"

def getGroupOrFail():
  if group == None:
    logger.log("Parameter 'group' is required by this command")
    raise ValueError("Parameter 'group' is required by this command")
  return group