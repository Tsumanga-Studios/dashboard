#!/usr/bin/env python3
"""
  Semi-automated deployment to s3

  deploy.py [options] version

  1. check that there are no changes outstanding in git status
  2. check that version is correct in setup.py and in multiplayer module
  3. make a git archive in /tmp named dashboard-X.Y.Z.zip (where X.Y.Z is the version)
  4. s3cmd sync the zip archive to s3://tsumanga-deploy

"""
import os
import subprocess
import argparse

def check_git_status():
    """ return output of git status as list of lines,
    empty if no output """
    git = subprocess.Popen(["git", "status", "-s"],
                           stdout=subprocess.PIPE,
                           universal_newlines=True)
    status_out, _ = git.communicate()
    return [line.strip() for line in status_out.strip().split("\n") if line.strip()]

def make_archive(version):
    """ make a git archive named according to version """
    path = "/tmp/dashboard-{0}.zip".format(version)
    subprocess.call(["git", "archive", "-o", path, "HEAD"])
    assert os.path.exists(path)
    return path

def sync_archive(path):
    """ sync archive into s3://tsumanga-deploy """
    subprocess.call(["s3cmd", "sync", path, "s3://tsumanga-deploy"])

def main():
    """ parse the command line and run the deployment """
    ap = argparse.ArgumentParser()
    add = ap.add_argument
    add("version", help="Version number X.Y.Z")
    opts = ap.parse_args()
    
    ok = True
    git_changes = check_git_status()
    if git_changes:
        print("* There are uncommitted changes:",
              *git_changes, sep="\n  ")
        ok = False
    import dashboard
    if dashboard.version != opts.version:
        print("* dashboard.version ==", dashboard.version)
        ok = False
    import setup
    if setup.version != opts.version:
        print("* setup.py version ==", setup.version)
        ok = False
    if not ok:
        print("FAIL")
        return
    archive_path = make_archive(opts.version)
    sync_archive(archive_path)
    print("SUCCESS")

if __name__ == '__main__':
    main()
