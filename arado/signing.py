# Software License Agreement (BSD License)
#
# Copyright (c) 2009-2011, Eucalyptus Systems, Inc.
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

import subprocess
import pexpect
import sys
import os
import re
import stat
from .exception import SigningError
from .exception import PathError

HOMEDIR = "GNUPGHOME"
RPMSIGN_CMD = 'rpmsign --define "_gpg_name %s" --define "__gpg_sign_cmd %%{__gpg} \
    gpg --force-v3-sigs --digest-algo=sha1 --batch --no-verbose --no-armor \
        --passphrase-fd 3 --no-secmem-warning -u \"%%{_gpg_name}\" \
            -sbo %%{__signature_filename} %%{__plaintext_filename}" --addsign %s'

KEY_RE = "^.*\(([\w\s]+)\).*$"

def sign_packages(packages, key_name, path='.', chroot=None):
    #if not key_name in get_keys():
        #raise SigningError, 'No key "%s" exists' % (key_name)
    if not packages:
        raise SigningError, "No packages supplied"

    signcmd = ""
    pkgpath = path
    if chroot:
        signcmd += "/usr/sbin/chroot %s " % (chroot)
        mount_cmd = "mount --bind %s %s" % (path, os.path.join(chroot, "mnt"))
        print "Mount Command: " + mount_cmd
        os.system(mount_cmd)
        pkgpath = "/mnt"
    signcmd += RPMSIGN_CMD

    package_list = " ".join([os.path.join(pkgpath, pkg) for pkg in packages])
    proc = pexpect.spawn(signcmd % (key_name, package_list), timeout=120)
    proc.logfile = sys.stdout
    proc.expect('Enter pass phrase: ')
    proc.send('\n')
    proc.expect(pexpect.EOF)
    proc.close()

    if chroot:
        os.system("umount %s" % (path))

    if proc.exitstatus != 0:
        raise SigningError, "Failed to sign RPM packages"

def set_gpghome(gpghome):
    expanded_gpghome = os.path.abspath(os.path.expanduser(gpghome))
    if not os.path.exists(expanded_gpghome):
        raise PathError, "GPG Home %s does not exist" % (gpghome)
    os.environ[HOMEDIR] = expanded_gpghome
    # Fix perms so we don't get warnings
    os.chmod(expanded_gpghome, stat.S_IRWXU)

def export_public_key(keyname):
    p = subprocess.Popen(["gpg", "--export", "-a", keyname],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, _ = p.communicate()
    return output

def export_public_key_file(keyname, filename):
    fp = open(filename, "wb")
    fp.write(export_public_key(keyname))
    fp.close()

def get_keys():
    p = subprocess.Popen(["gpg", "-K"], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    output, _ = p.communicate()
    keys = []
    for line in output.split("\n"):
        if line.startswith("uid"):
            try:
                key = re.match(KEY_RE, line).groups(0)[0]
                key = key.split(" ")[0]
                keys.append(key)
            except Exception:
                pass
    return keys

