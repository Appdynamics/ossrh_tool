import os
import unittest
import requests_mock
import requests
import logger
from cli import main
import re
import config

BASE_URL="https://oss.sonatype.org/service/local"
UPLOADS_URL=BASE_URL + "/staging/deploy/maven2/"
STAGING_REPOS_URL=BASE_URL + "/staging/profile_repositories"
ACTION_CLOSE_URL=BASE_URL + "/staging/bulk/close"
ACTION_DROP_URL=BASE_URL + "/staging/bulk/drop"
ACTION_PROMOTE_URL=BASE_URL + "/staging/bulk/promote"
INSPECT_URL=BASE_URL + "/repositories/"

here=os.path.dirname(os.path.realpath(__file__))

# Output capture boilerplate
capturedOutput=""
def recorder(txt, no_NL=False):
    global capturedOutput
    capturedOutput += txt + ('' if no_NL else '\n')
logger.log = recorder

def static_matcher(request):
    match = re.search(r'^/service/local((?:/[0-9a-z._-]+)+)/?$', request.path_url)
    if match != None:
        resp = requests.Response()
        f = open(here + "/test-fixtures" + match.group(1) + ".xml")
        resp.raw = f
        return resp
    return None

def sequence_matcher(m, seq):
    global request_nr
    request_nr = 0
    def matcher(request):
        global request_nr
        request_nr += 1
        if len(seq) <= request_nr - 1:
            raise AssertionError("Unexpected request: " + request.path_url)
        
        spec = seq[request_nr - 1]
        if request.url != spec['url']:
            raise AssertionError("Wrong URL. Got '" + request.path_url + "', expected '" + spec['url'] + "'")
        if request.method != spec['method']:
            raise AssertionError("Wrong method. Got '" + request.method + "', expected '" + spec['method'] + "'")
        
        resp = requests.Response()
        if 'body' in spec:
            resp.raw = spec['body']
        return resp
    
    return matcher


class MainTest(unittest.TestCase):

    def setUp(self):
        config.creds = None
        config.agent = None
        config.group = None

    @requests_mock.mock()
    def test_list_repos_no_params(self, m):
        global capturedOutput
        m.add_matcher(static_matcher)

        capturedOutput=""
        try:
            main(['list'])
            raise AssertionError("Was expected to throw")
        except ValueError:
            self.assertEquals(
"""Please specify at least one of '--agent' or '--group'
""", capturedOutput)

    @requests_mock.mock()
    def test_list_repos_happy(self, m):
        global capturedOutput
        m.add_matcher(static_matcher)

        capturedOutput=""
        main(['--group', 'com.example', 'list'])
        self.assertEquals(
"""  agent                                 |   repository ID               |   state
--------------------                    | --------------------          | --------------------
BC72ZFoAEIbbM2p5aDcWgZeOgCLnvfgm        | comexample-1093               | []
4J5c83HM5216KgSa5Hjzp9B4NA2U8bd1        | comexample-1095               | ['closed']
python-requests/2.19.1                  | comexample-1097               | ['closed']
GHgvBjb7fCZYfTtVEJ3n5Hf2IfYJbNQA        | comexample-1098               | []
zFM2DfDs1ciDgfDHB2VR0uILjsYTQUzq        | comexample-1099               | ['transitioning']
lGRwQVjh1UQlUUZ5pPLuaFMHqNORlIC3        | comexample-1100               | ['closed']
""", capturedOutput)

    @requests_mock.mock()
    def test_list_repos_agent(self, m):
        global capturedOutput
        m.add_matcher(static_matcher)

        capturedOutput=""
        main(['--agent', 'GHgvBjb7fCZYfTtVEJ3n5Hf2IfYJbNQA', 'list'])
        self.assertEquals(
"""  agent                                 |   repository ID               |   state
--------------------                    | --------------------          | --------------------
GHgvBjb7fCZYfTtVEJ3n5Hf2IfYJbNQA        | comexample-1098               | []
""", capturedOutput)

    @requests_mock.mock()
    def test_list_repos_empty(self, m):
        global capturedOutput
        m.add_matcher(static_matcher)

        capturedOutput=""
        main(['--agent', 'does not exist', 'list'])
        self.assertEquals(
"""No repository found
""", capturedOutput)

    @requests_mock.mock()
    def test_close_repo(self, m):
        global capturedOutput
        with open(here + '/test-fixtures/staging/profile_repositories.transitioning.xml', 'r') as resp_transitioning:
            with open(here + '/test-fixtures/staging/profile_repositories.closed.xml', 'r') as resp_closed:

                m.add_matcher(sequence_matcher(m, [
                    {"method": 'POST', "url": ACTION_CLOSE_URL},
                    {"method": 'GET', "url": STAGING_REPOS_URL, "body": resp_transitioning},
                    {"method": 'GET', "url": STAGING_REPOS_URL, "body": resp_closed}
                ]))

                capturedOutput=""
                main(['close', 'comexample-1098'])
                self.assertEquals(
"""Closing 'comexample-1098'
Waiting for repo 'comexample-1098' to stop transitioning.....
Success.
""", capturedOutput)

    @requests_mock.mock()
    def test_close_repo_fail(self, m):
        global capturedOutput
        with open(here + '/test-fixtures/staging/profile_repositories.transitioning.xml', 'r') as resp_transitioning:
            with open(here + '/test-fixtures/staging/profile_repositories.xml', 'r') as resp_open:

                m.add_matcher(sequence_matcher(m, [
                    {"method": 'POST', "url": ACTION_CLOSE_URL},
                    {"method": 'GET', "url": STAGING_REPOS_URL, "body": resp_transitioning},
                    {"method": 'GET', "url": STAGING_REPOS_URL, "body": resp_open}
                ]))

                capturedOutput=""
                try:
                    main(['close', 'comexample-1098'])
                    raise AssertionError("Was expected to throw")
                except ValueError:
                    self.assertEquals(
"""Closing 'comexample-1098'
Waiting for repo 'comexample-1098' to stop transitioning.....
""", capturedOutput)

    @requests_mock.mock()
    def test_close_repo_server_error(self, m):
        global capturedOutput
        m.register_uri('POST', ACTION_CLOSE_URL, status_code=500)

        capturedOutput=""
        try:
            main(['close', 'comexample-000'])
            raise AssertionError("Was expected to throw")
        except IOError:
            self.assertEquals(
"""Closing 'comexample-000'
Error: 500

""", capturedOutput)

    @requests_mock.mock()
    def test_drop_repo(self, m):
        global capturedOutput
        with open(here + '/test-fixtures/staging/profile_repositories.transitioning.xml', 'r') as resp_transitioning:
            with open(here + '/test-fixtures/staging/profile_repositories.gone.xml', 'r') as resp_gone:

                m.add_matcher(sequence_matcher(m, [
                    {"method": 'POST', "url": ACTION_DROP_URL},
                    {"method": 'GET', "url": STAGING_REPOS_URL, "body": resp_transitioning},
                    {"method": 'GET', "url": STAGING_REPOS_URL, "body": resp_gone}
                ]))

                capturedOutput=""
                main(['drop', 'comexample-1098'])
                self.assertEquals(
"""Dropping 'comexample-1098'
Waiting for repo 'comexample-1098' to stop transitioning.....
Success.
""", capturedOutput)

    @requests_mock.mock()
    def test_drop_repo_fail(self, m):
        global capturedOutput
        with open(here + '/test-fixtures/staging/profile_repositories.transitioning.xml', 'r') as resp_transitioning:
            with open(here + '/test-fixtures/staging/profile_repositories.xml', 'r') as resp_open:
                m.add_matcher(sequence_matcher(m, [
                    {"method": 'POST', "url": ACTION_DROP_URL},
                    {"method": 'GET', "url": STAGING_REPOS_URL, "body": resp_transitioning},
                    {"method": 'GET', "url": STAGING_REPOS_URL, "body": resp_open}
                ]))

                capturedOutput=""
                try:
                    main(['drop', 'comexample-1098'])
                    raise AssertionError("Was expected to throw")
                except ValueError:
                    self.assertEquals(
"""Dropping 'comexample-1098'
Waiting for repo 'comexample-1098' to stop transitioning.....
""", capturedOutput)

    @requests_mock.mock()
    def test_publish_no_group(self, m): # The program should fail if we attempt to publish while there are multiple candidates to release
        global capturedOutput
        m.add_matcher(static_matcher)

        capturedOutput=""
        try:
            main(['publish'])
            raise AssertionError("Was expected to throw")
        except ValueError:
            self.assertEquals(
"""=== Releasing ossrh staging repo ===
Looking for staging repositories...
Please specify at least one of '--agent' or '--group'
""", capturedOutput)

    @requests_mock.mock()
    def test_publish_multiple_candidates(self, m): # The program should fail if we attempt to publish while there are multiple candidates to release
        global capturedOutput
        m.add_matcher(static_matcher)

        capturedOutput=""
        try:
            main(['--group', 'com.example', 'publish'])
            raise AssertionError("Was expected to throw")
        except ValueError:
            self.assertEquals(
"""=== Releasing ossrh staging repo ===
Looking for staging repositories...
""", capturedOutput)

    @requests_mock.mock()
    def test_publish_dry_run(self, m):
        global capturedOutput
        with open(here + '/test-fixtures/staging/profile_repositories.xml', 'r') as resp_open:
            with open(here + '/test-fixtures/staging/profile_repositories.closed.xml', 'r') as resp_closed:
                with open(here + '/test-fixtures/staging/profile_repositories.gone.xml', 'r') as resp_gone:
                    m.add_matcher(sequence_matcher(m, [
                        {"method": 'GET', "url": STAGING_REPOS_URL, "body": resp_open},
                        {"method": 'POST', "url": ACTION_CLOSE_URL},
                        {"method": 'GET', "url": STAGING_REPOS_URL, "body": resp_closed},
                        {"method": 'POST', "url": ACTION_DROP_URL},
                        {"method": 'GET', "url": STAGING_REPOS_URL, "body": resp_gone}
                    ]))

                    capturedOutput=""
                    main(['--agent', 'GHgvBjb7fCZYfTtVEJ3n5Hf2IfYJbNQA', 'publish', '--dry-run'])
                    self.assertEquals(
"""Dryrun enabled. This will not actually publish the project.
=== Releasing ossrh staging repo ===
Looking for staging repositories...
Closing repo 'comexample-1098'...
Waiting for repo 'comexample-1098' to stop transitioning....
Success.
This is a dry run. I will now drop the repository instead of publishing it.
Waiting for repo 'comexample-1098' to stop transitioning....
Success.
""", capturedOutput)

    @requests_mock.mock()
    def test_publish_success(self, m):
        global capturedOutput
        with open(here + '/test-fixtures/staging/profile_repositories.xml', 'r') as resp_open:
            with open(here + '/test-fixtures/staging/profile_repositories.closed.xml', 'r') as resp_closed:
                with open(here + '/test-fixtures/staging/profile_repositories.gone.xml', 'r') as resp_gone:
                    m.add_matcher(sequence_matcher(m, [
                        {"method": 'GET', "url": STAGING_REPOS_URL, "body": resp_open},
                        {"method": 'POST', "url": ACTION_CLOSE_URL},
                        {"method": 'GET', "url": STAGING_REPOS_URL, "body": resp_closed},
                        {"method": 'POST', "url": ACTION_PROMOTE_URL},
                        {"method": 'GET', "url": STAGING_REPOS_URL, "body": resp_gone}
                    ]))

                    capturedOutput=""
                    main(['--agent', 'GHgvBjb7fCZYfTtVEJ3n5Hf2IfYJbNQA', 'publish'])
                    self.assertEquals(
"""=== Releasing ossrh staging repo ===
Looking for staging repositories...
Closing repo 'comexample-1098'...
Waiting for repo 'comexample-1098' to stop transitioning....
Success.
Releasing the repo 'comexample-1098'...
Waiting for repo 'comexample-1098' to stop transitioning....
Success.
""", capturedOutput)

#     @requests_mock.mock()
#     def test_release_repo_fail(self, m):
#         global capturedOutput
#         global request_nr
#         with open(here + '/test-fixtures/staging/profile_repositories.transitioning.xml', 'r') as resp_transitioning:
#             with open(here + '/test-fixtures/staging/profile_repositories.xml', 'r') as resp_open:

#                 m.add_matcher(sequence_matcher(m, [
#                     {"method": 'POST', "url": ACTION_DROP_URL},
#                     {"method": 'GET', "url": STAGING_REPOS_URL, "body": resp_transitioning},
#                     {"method": 'GET', "url": STAGING_REPOS_URL, "body": resp_open}
#                 ]))

#                 capturedOutput=""
#                 try:
#                     main(['drop', 'comexample-1098'])
#                     raise AssertionError("Was expected to throw")
#                 except ValueError:
#                     self.assertEquals(
# """Dropping 'comexample-1098'
# Waiting for repo 'comexample-1098' to stop transitioning.....
# """, capturedOutput)

    @requests_mock.mock()
    def test_inspect(self, m):
        global capturedOutput
        m.add_matcher(static_matcher)

        capturedOutput=""
        main(['inspect', 'comexample-1098'])
        self.assertEquals(
"""https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-gradle-plugin/4.5.0.1068/example-gradle-plugin-4.5.0.1068-sources.jar.md5
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-gradle-plugin/4.5.0.1068/example-gradle-plugin-4.5.0.1068.jar
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-gradle-plugin/4.5.0.1068/example-gradle-plugin-4.5.0.1068.jar.asc
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-gradle-plugin/4.5.0.1068/example-gradle-plugin-4.5.0.1068-javadoc.jar.asc
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-gradle-plugin/4.5.0.1068/example-gradle-plugin-4.5.0.1068-javadoc.jar.md5
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-gradle-plugin/4.5.0.1068/example-gradle-plugin-4.5.0.1068-sources.jar.asc
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-gradle-plugin/4.5.0.1068/example-gradle-plugin-4.5.0.1068.jar.md5
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-gradle-plugin/4.5.0.1068/example-gradle-plugin-4.5.0.1068.jar.sha1
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-gradle-plugin/4.5.0.1068/example-gradle-plugin-4.5.0.1068-sources.jar
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-gradle-plugin/4.5.0.1068/example-gradle-plugin-4.5.0.1068.pom
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-gradle-plugin/4.5.0.1068/example-gradle-plugin-4.5.0.1068-sources.jar.sha1
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-gradle-plugin/4.5.0.1068/example-gradle-plugin-4.5.0.1068.pom.asc
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-gradle-plugin/4.5.0.1068/example-gradle-plugin-4.5.0.1068.pom.sha1
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-gradle-plugin/4.5.0.1068/example-gradle-plugin-4.5.0.1068.pom.md5
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-gradle-plugin/4.5.0.1068/example-gradle-plugin-4.5.0.1068-javadoc.jar
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-gradle-plugin/4.5.0.1068/example-gradle-plugin-4.5.0.1068-javadoc.jar.sha1
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-injector/4.5.0.1068/example-injector-4.5.0.1068.pom
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-injector/4.5.0.1068/example-injector-4.5.0.1068-sources.jar
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-injector/4.5.0.1068/example-injector-4.5.0.1068.jar.sha1
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-injector/4.5.0.1068/example-injector-4.5.0.1068.pom.md5
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-injector/4.5.0.1068/example-injector-4.5.0.1068-sources.jar.sha1
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-injector/4.5.0.1068/example-injector-4.5.0.1068.pom.sha1
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-injector/4.5.0.1068/example-injector-4.5.0.1068-javadoc.jar
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-injector/4.5.0.1068/example-injector-4.5.0.1068-javadoc.jar.asc
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-injector/4.5.0.1068/example-injector-4.5.0.1068-javadoc.jar.sha1
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-injector/4.5.0.1068/example-injector-4.5.0.1068.pom.asc
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-injector/4.5.0.1068/example-injector-4.5.0.1068.jar.asc
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-injector/4.5.0.1068/example-injector-4.5.0.1068.jar
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-injector/4.5.0.1068/example-injector-4.5.0.1068-sources.jar.md5
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-injector/4.5.0.1068/example-injector-4.5.0.1068-sources.jar.asc
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-injector/4.5.0.1068/example-injector-4.5.0.1068-javadoc.jar.md5
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-injector/4.5.0.1068/example-injector-4.5.0.1068.jar.md5
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-runtime/4.5.0.1068/example-runtime-4.5.0.1068-javadoc.jar.asc
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-runtime/4.5.0.1068/example-runtime-4.5.0.1068-sources.jar
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-runtime/4.5.0.1068/example-runtime-4.5.0.1068-javadoc.jar.sha1
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-runtime/4.5.0.1068/example-runtime-4.5.0.1068.jar.md5
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-runtime/4.5.0.1068/example-runtime-4.5.0.1068-sources.jar.md5
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-runtime/4.5.0.1068/example-runtime-4.5.0.1068-sources.jar.sha1
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-runtime/4.5.0.1068/example-runtime-4.5.0.1068.pom.asc
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-runtime/4.5.0.1068/example-runtime-4.5.0.1068-javadoc.jar
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-runtime/4.5.0.1068/example-runtime-4.5.0.1068.jar.sha1
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-runtime/4.5.0.1068/example-runtime-4.5.0.1068.pom.md5
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-runtime/4.5.0.1068/example-runtime-4.5.0.1068.jar.asc
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-runtime/4.5.0.1068/example-runtime-4.5.0.1068-sources.jar.asc
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-runtime/4.5.0.1068/example-runtime-4.5.0.1068-javadoc.jar.md5
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-runtime/4.5.0.1068/example-runtime-4.5.0.1068.jar
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-runtime/4.5.0.1068/example-runtime-4.5.0.1068.pom.sha1
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/com/example/example-runtime/4.5.0.1068/example-runtime-4.5.0.1068.pom
https://oss.sonatype.org/service/local/repositories/comexample-1098/content/archetype-catalog.xml
""", capturedOutput)


if __name__ == '__main__':
    unittest.main()
