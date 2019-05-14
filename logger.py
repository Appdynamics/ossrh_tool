import sys

def default_log(txt, no_NL=False):
    if no_NL:
        sys.stdout.write(txt)
    else:
        print(txt)

log = default_log
