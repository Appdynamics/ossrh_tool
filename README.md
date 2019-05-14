OSSRH tool
==========

A command line utility for publishing through OSSRH.

## Purpose

This tool lets you publish maven packages to maven central through [oss.sonatype.org](https://oss.sonatype.org) from the command line. It is intended for automation and when standard gradle/maven plugins can't be used.

## Prerequisites

Python 2.7

### 1. Credentials

Create an account in sonatype and follow the initial setup steps in the guide at https://central.sonatype.org/pages/ossrh-guide.html .
Load your credentials in environment variables `OSSRH_USERNAME` and `OSSRH_PASSWORD`.

### 2. Project structure

The project you would like to upload should consist of binary, sources and javadoc jars, as well as a pom file, all of them already signed with your private key. All these artifacts should be flat in the same directory, and be named `{project}-{version}{-qualifier?}.{extension}`.

For instance:

    - my-archive/
        - myproject-1.2.3.pom
        - myproject-1.2.3.pom.asc
        - myproject-1.2.3.jar
        - myproject-1.2.3.jar.asc
        - myproject-1.2.3-javadoc.jar
        - myproject-1.2.3-javadoc.jar.asc
        - myproject-1.2.3-sources.jar
        - myproject-1.2.3-sources.jar.asc

### 3. Agent ID

Generate a unique string. This will be your "agent ID". Think of it like a session ID which is used to uniquely identify your own session. If someone else (or another CI/CD build host) is using the repository at the same time as you, the tool will not get confused because both of you are using different agent IDs.

## Publishing a project

Publishing is a two step process.

First, upload the artifacts to a staging repository:

`python ossrh_tool --group com.example --agent your-agent-id upload my-archive/ myproject 1.2.3`

Second, publish the staging repository:

`python ossrh_tool --agent your-agent-id publish`

Alternatively, of you just want to test that you can publish, but don't actually want to publish, use the `--dry-run` flag. This allows you to develop your CI/CD pipeline without accidentally publishing something.

`python ossrh_tool --agent your-agent-id publish --dry-run`

## Advanced usage

### Scoping

All of the commands are scoped with the `--group` and `--agent` parameters, such that you can only see and interact with repositories which match these filters. Note that `--group` and `--agent` must be specified before the command.

### Commands reference

- `publish [options]`: close and publish the staging repo. The command fails if there is not exacly one staging repo available.
  - options:
    - `--dry-run`: Does not actually publish to maven central. Drops the staging repository instead.
- `list`: Lists available staging repositories.
- `close <repo>`: Closes the given staging repository.
- `drop <repo|--all>`: Drops the staging repository, or all repositories if --all is provided.
- `upload <sourceDir> <projectName> <projectVersion>`: Uploads project artifacts to the staging repository. This automatically creates a new repository if none currently exist.
- `inspect <repository>`: Prints the contents of a given repository. Useful for checking that everything is there before shipping.
- `help`: Prints usage instructions
