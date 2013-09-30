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

import os
import re
import stat
import subprocess
import sys

import pexpect

from .exception import SigningError
from .utils import CommandEnvironment as CmdEnv

RPMSIGN_CMD = 'rpmsign --define "_gpg_name %s" \
        --define "__gpg_sign_cmd %%{__gpg} gpg --force-v3-sigs \
        --digest-algo=sha1 --batch --no-verbose --no-armor \
        --passphrase-fd 3 --no-secmem-warning -u \"%%{_gpg_name}\" \
        -sbo %%{__signature_filename} %%{__plaintext_filename}" \
        --addsign %s'

KEY_RE = "sec.*\/\([\w]+\).*"


def sign_packages(packages, key_id, path='.', chroot=None):
    if key_id not in get_key_ids():
        raise SigningError("key '{0}' not found".format(key_id))
    if not packages:
        return

    with CmdEnv(chroot=chroot, src=path, dst='/mnt') as env:
        package_list = " ".join([os.path.join(env.dst, pkg) for pkg in packages])
        proc = env.call_with_expect(RPMSIGN_CMD % (key_id, package_list))
        proc.expect('Enter pass phrase: ')
        proc.send('\n')
        proc.expect(pexpect.EOF)
        proc.close()
        if proc.exitstatus != 0:
            raise SigningError("signing packages failed")


def set_gpghome(gpghome):
    expanded_gpghome = os.path.abspath(os.path.expanduser(gpghome))
    if not os.path.exists(expanded_gpghome):
        raise ValueError("path '{0}' does not exist".format(gpghome))
    os.environ['GNUPGHOME'] = expanded_gpghome
    # Fix perms so we don't get warnings
    os.chmod(expanded_gpghome, stat.S_IRWXU)


def export_public_key(keyname):
    p = subprocess.Popen(["gpg", "--export", "-a", keyname],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.communicate()[0]


def export_public_key_file(keyname, filename):
    with open(filename, "wb") as fp:
        fp.write(export_public_key(keyname))


def get_key_ids():
    p = subprocess.Popen(["gpg", "-K"], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    output, _ = p.communicate()
    keys = []
    for line in output.split("\n"):
        if line.startswith("sec"):
            try:
                key = re.search(r'/([\w]+)', line).groups()[0]
                keys.append(key)
            except Exception:
                pass
    return keys
