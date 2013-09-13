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
import fnmatch
import glob
import os
import shutil
import stat
from subprocess import check_call, CalledProcessError
import tempfile

# Third party libraries
from BeautifulSoup import BeautifulSoup

# Local libraries
from .config import get_config
from .signing import sign_packages
from .exception import SigningError, PromotionError
from .utils import CommandEnvironment as CmdEnv

NEW_REPO_TEMPL = {
    "dirs": [
        "rhel/6",
    ],
    "links": [
        ["rhel", "centos"],
        ["6", "rhel/6Server"],
        ["6", "rhel/6Workstation"],
    ]
}


def walkerror(error):
    pass


def merge(source, dest, signingkey=None):
    config = get_config()
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
            print("Info: creating directory '{0}'".format(dest_root))
            os.mkdir(dest_root)

        # os.chown(dest_root, config.uid, config.gid)
        # os.chmod(dest_root, int(config.general().get('dirperms')))

        for f in files:
            dest_file = os.path.join(dest_root, f)
            if os.path.islink(dest_file):
                print "Info: skipping symlink {0}".format(f)
                continue
            if os.path.exists(dest_file):
                print "Info: skipping duplicate {0}".format(f)
            else:
                shutil.copy2(os.path.join(root, f), dest_root)
                # os.chown(dest_file, config.uid, config.gid)
                # os.chmod(dest_file, int(config.general().get('fileperms')))
    # Rebuild repository metadata
    for repo_dir in repo_dirs:
        if signingkey:
            sign(repo_dir, signingkey)
        rebuild(repo_dir)


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
    tmpdir = get_config().paths().get('repotemp', '/var/tmp')
    path_tmp = tempfile.mkdtemp(dir=tmpdir)
    os.chmod(path_tmp,
             stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH |
             stat.S_IXOTH | stat.S_ISGID)
    if os.path.exists(path) and merge:
        cmd = ['cp', '-a', os.path.join(path, '.'), path_tmp]
        try:
            check_call(cmd)
        except CalledProcessError as err:
            raise PromotionError("Failed to create temporary repository with status {0}".format(err.returncode))
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
                rebuild(archdir)


def rebuild(path, comps_file=None, chroot=None):
    print("Info: createrepo on {0}".format(path))
    cmd = ["/usr/bin/createrepo"]

    # Clear all repository metadata
    shutil.rmtree(os.path.join(path, "repodata"), ignore_errors=True)

    with CmdEnv(chroot=chroot, src=path) as env:
        try:
            if comps_file is None:
                comps_file = glob.glob(os.path.join(path, "*xml"))[0]
            if env.is_mounted:
                comps_file = os.path.join(env.dst,
                                          os.path.basename(comps_file))

            if not os.path.exists(comps_file):
                raise Exception("file {0} does not exist".format(comps_file))

            cmd += ["-g", comps_file]
            print("Info: using comps file '{0}'".format(comps_file))
        except Exception as err:
            print("Info: no comps file found; skipping")

        cmd += [
            "--checksum=sha",
            "--update",
            "--skip-symlinks",
            "-x", "*release-internal*",
            "--unique-md-filenames",
            "--no-database",
            env.dst,
        ]


        print "executing command: {0}".format(cmd)
        env.call(cmd)

def replace(source_path, dest_path):
    dest_path_temp = dest_path + "-temp"
    if os.path.exists(dest_path):
        os.rename(dest_path, dest_path_temp)
    shutil.move(source_path, dest_path)
    if os.path.exists(dest_path_temp):
        shutil.rmtree(dest_path_temp)
