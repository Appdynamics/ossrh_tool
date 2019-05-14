"""
A commnand line interface to interact with Sonatype's ossrh programmatically!
"""

import os
import sys
import ossrh
import config
import logger

def help():
  logger.log("Usage: ossrh_tool.py [--agent <agent>] [--group <group>] <command>")
  logger.log("")
  logger.log("Manage nexus OSSRH staging repos from the command line!")
  logger.log("")
  logger.log("REQUIRED environment variables:")
  logger.log("    OSSRH_USERNAME and OSSRH_PASSWORD")
  logger.log("")
  logger.log("Options:")
  logger.log("    --agent   : unique id to isolate yourself from other users. Artifacts you upload will be tied to this agent and")
  logger.log("                the working set of repositories will be scoped to this specific agent.")
  logger.log("    --group   : artifact group in reverse-dns notation. For instance: 'com.example.department'")
  logger.log("Available commands:")
  logger.log("    publish [options]")
  logger.log("        close and publish the staging repo. The command fails if there is not exacly one staging repo available.")
  logger.log("        options:")
  logger.log("            --dry-run : Does not actually publish to maven central. Drops the staging repository instead.")
  logger.log("            --interactive : Pauses between each step such that the user can manually test the release to be.")
  logger.log("    list")
  logger.log("        Lists available staging repositories.")
  logger.log("    close <repo>")
  logger.log("        Closes the given staging repository.")
  logger.log("    drop <repo|--all>")
  logger.log("        Drops the staging repository, or all repositories if --all is provided.")
  logger.log("    upload <sourceDir> <projectName> <projectVersion>")
  logger.log("        Uploads project artifacts to the staging repository. This automatically creates a new repository if none currently exist.")
  logger.log("    inspect <repository>")
  logger.log("        Prints the contents of a given repository. Useful for checking that everything is there before shipping.")
  logger.log("    help")
  logger.log("        Prints this help message")

def bad_usage_error(message):
  logger.log("Error: " + message + "\n")
  help()
  raise ValueError(message)

# Gets the credentials from environment variables
def get_ossrh_credentials():
    return ( os.environ['OSSRH_USERNAME'], os.environ['OSSRH_PASSWORD'] )

def log_list_line(agent, name, state):
  logger.log("{:40.40s}| {:30.30s}| {}".format(agent, name, state))

def get_single_repo(maybeName):
  if maybeName != None:
    return ossrh.StagingRepository(maybeName)
  # Else, try to find a single repo. Fail if there is not exactly one repo available.
  repos = ossrh.find_all_staging_repositories()
  if len(repos) == 0:
    raise ValueError("Error: No staging repository found!")
  elif len(repos) > 1:
    raise ValueError("Error: There are more than one repos currently open. Use `python ossrh_tool.py drop --all` to erase previous repos.")

  return ossrh.StagingRepository(repos[0].name)


def do_list(args):
  if len(args) > 0:
    bad_usage_error("Too many parameters. Expected no parameter.")

  repos = ossrh.find_all_staging_repositories()
  if len(repos) > 0:
    log_list_line("  agent", "  repository ID", "  state")
    log_list_line("--------------------", "--------------------", "--------------------")
    for repoNode in repos:
      log_list_line(repoNode.agent, repoNode.name, repoNode.get_attrs())
  else:
    logger.log("No repository found")

def do_drop(args):
  arg0=None
  if len(args) > 0:
    arg0 = args[0]

  if arg0 == '--all':
    logger.log("Dropping all repos")
    for repoNode in ossrh.find_all_staging_repositories():
      repo = ossrh.StagingRepository(repoNode.name)
      logger.log("Dropping '" + repo.name + "'")
      repo.drop()
  else:
    repo = get_single_repo(arg0)
    logger.log("Dropping '" + repo.name + "'")
    repo.drop()

def do_close(args):
  arg0=None
  if len(args) > 0:
    arg0 = args[0]
  repo = get_single_repo(arg0)

  logger.log("Closing '" + repo.name + "'")
  repo = ossrh.StagingRepository(repo.name)
  repo.close()

def do_publish(args):
  dryrun = False
  interactive = False
  repoName = None
  while len(args) > 0:
    if args[0] == '--dry-run':
      logger.log("Dryrun enabled. This will not actually publish the project.")
      dryrun=True
    else:
      repoName = args[0]
    args = args[1:]

  if interactive and not dryrun:
    raise ValueError("--interactive is not meant to be used for real publishing. Please use in conjunction with --dry-run.")

  logger.log("=== Releasing ossrh staging repo ===")

  logger.log("Looking for staging repositories...")
  repo = get_single_repo(repoName)
  
  logger.log("Closing repo '" + repo.name + "'...")
  repo.close()

  if dryrun == True:
    logger.log("This is a dry run. I will now drop the repository instead of publishing it.")
    repo.drop()
  else:
    logger.log("Releasing the repo '" + repo.name + "'...")
    repo.release()

def do_upload(args):
  if len(args) != 3:
    bad_usage_error("Invalid number of parameters. Expected 3 but got " + str(len(args)))
  
  project_dir = args[0]
  project_name = args[1]
  project_version = args[2]

  ossrh.upload_artifact(project_dir, project_name, project_version, '.pom', hash=True)
  ossrh.upload_artifact(project_dir, project_name, project_version, '.pom.asc', hash=False)
  ossrh.upload_artifact(project_dir, project_name, project_version, '.jar', hash=True)
  ossrh.upload_artifact(project_dir, project_name, project_version, '.jar.asc', hash=False)
  ossrh.upload_artifact(project_dir, project_name, project_version, '-sources.jar', hash=True)
  ossrh.upload_artifact(project_dir, project_name, project_version, '-sources.jar.asc', hash=False)
  ossrh.upload_artifact(project_dir, project_name, project_version, '-javadoc.jar', hash=True)
  ossrh.upload_artifact(project_dir, project_name, project_version, '-javadoc.jar.asc', hash=False)
  
  ossrh.upload_metadata(project_dir, project_name, project_version)


def do_inspect(args):
  if len(args) != 1:
    bad_usage_error("Invalid number of parameters. Expected 1 but got " + str(len(args)))
  repo = ossrh.StagingRepository(args[0])
  repo.inspect()

def main(args):
  if len(args) < 1:
    bad_usage_error("Not enough arguments")

  while len(args) > 1:
    if args[0] == "--agent":
      config.agent = args[1]
      args = args[2:]
    elif args[0] == "--group":
      config.group = args[1]
      args = args[2:]
    else:
      break

  cmd=args[0]
  cmd_args=args[1:]

  # Loads credentials globally, we will need them no matter what
  try:
    config.creds = get_ossrh_credentials()
  except:
    bad_usage_error("OSSRH credentials not set!")

  if cmd == 'publish':
    do_publish(cmd_args)
  elif cmd == 'list':
    do_list(cmd_args)
  elif cmd == 'drop':
    do_drop(cmd_args)
  elif cmd == 'close':
    do_close(cmd_args)
  elif cmd == 'upload':
    do_upload(cmd_args)
  elif cmd == 'inspect':
    do_inspect(cmd_args)
  else:
    help()
    sys.exit(1)
