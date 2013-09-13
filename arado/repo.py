# Software License Agreement (BSD License)
#
# Copyright (c) 2012-2013, Eucalyptus Systems, Inc.
# All rights reserved.
#
# Redistribution and use of this software in source and binary forms, with or
# without modification, are permitted provided that the following conditions
# are met:
#
#   Redistributions of source code must retain the above
#   copyright notice, this list of conditions and the
#   following disclaimer.
#
#   Redistributions in binary form must reproduce the above
#   copyright notice, this list of conditions and the
#   following disclaimer in the documentation and/or other
#   materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Author: Matt Spaulding mspaulding@eucalyptus.com

# Core libraries
import os
import glob
import fnmatch
import tempfile
import shutil
import subprocess
import stat

# Third party libraries
from BeautifulSoup import BeautifulSoup

# Local libraries
from .exception import SigningError, PromotionError

NEW_REPO_TEMPL = {
    "dirs": [
        "rhel/5",
        "rhel/6",
    ],
    "links": [
        ["rhel", "centos"],
        ["5", "rhel/5Server"],
        ["6", "rhel/6Server"],
        ["6", "rhel/6Workstation"],
    ]
}


def walkerror(error):
    pass


def merge(source, dest, signingkey=None):
    repo_dirs = []
    # Copy only original files
    print("Info: copying files")
    for root, dirs, files in os.walk(source, onerror=walkerror):
        dest_root = root.replace(source, dest)

        # Mark directories for which we will rebuild repository metadata
        if dest_root.endswith("/repodata"):
            repo_dirs.append(os.path.dirname(dest_root))
            continue

        if not os.path.exists(dest_root):
            print("Info: creating directory '{}'".format(dest_root))
            os.mkdir(dest_root)

        for f in files:
            dest_file = os.path.join(dest_root, f)
            if os.path.islink(dest_file):
                print "Info: skipping symlink " + f
                continue
            if os.path.exists(dest_file):
                print "Info: skipping duplicate " + f
            else:
                shutil.copy2(os.path.join(root, f), dest_root)
    # Rebuild repository metadata
    for repo_dir in repo_dirs:
        if signingkey:
            sign_repo(repo_dir, signingkey)
        rebuild_repo(repo_dir)


def sign(repo, signingkey):
    for root, dirs, files in os.walk(repo, onerror=walkerror):
        try:
            pkglist = []
            for pkg in fnmatch.filter(files, "*.rpm"):
                if not os.path.islink(os.path.join(root, pkg)):
                    pkglist.append(pkg)
            sign_packages(pkglist, signingkey, path=root)
        except SigningError, e:
            print(e)


def stage(path, merge=False):
    path_tmp = tempfile.mkdtemp(dir="/srv/software/.repotmp")
    os.chmod(path_tmp,
             stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH |
             stat.S_IXOTH | stat.S_ISGID)
    if os.path.exists(path) and merge:
        cmd = ['cp', '-a', os.path.join(path, '.'), path_tmp]
        p = subprocess.Popen(cmd)
        p.communicate()
        if p.returncode > 0:
            raise PromotionError("Failed to create temporary repository")
    else:
        print("Info: creating repository template")
        for d in NEW_REPO_TEMPL["dirs"]:
            os.makedirs(os.path.join(path_tmp, d))
        for link in NEW_REPO_TEMPL["links"]:
            os.symlink(link[0], os.path.join(path_tmp, link[1]))
    return path_tmp


def rebuild_all(toplevel):
    for d in NEW_REPO_TEMPL["dirs"]:
        for arch in ("i386", "x86_64"):
            archdir = os.path.join(toplevel, d, arch)
            if os.path.isdir(archdir):
                rebuild_repo(archdir)


def rebuild(path, chroot=None):
    print("Info: createrepo on " + path)
    cmd = ["/usr/bin/createrepo"]

    with CommandEnvironment(chroot=chroot, src=path) as env:
        comps_file = None
        try:
            comps_file = glob.glob(os.path.join(path, "*xml"))[0]
            if env.is_mounted:
                comps_file = os.path.join(env.dst,
                                          os.path.basename(comps_file))

            cmd += ["-g", comps_file]
            print("Info: using comps file '{}'".format(comps_file))
        except Exception, e:
            print("Info: no comps file found")

        cmd += [
            "--checksum=sha",
            "--update",
            "--skip-symlinks",
            "--unique-md-filenames",
            env.dst,
        ]

        exitcode = env.exec_with_stdout(cmd, cwd=env.dst)['exitcode']
        if exitcode > 0:
            raise PromotionError("Failed to rebuild repository")


def replace(source_path, dest_path):
    dest_path_temp = dest_path + "-temp"
    if os.path.exists(dest_path):
        os.rename(dest_path, dest_path_temp)
    shutil.move(source_path, dest_path)
    if os.path.exists(dest_path_temp):
        shutil.rmtree(dest_path_temp)
