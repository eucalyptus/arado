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
from subprocess import check_call, CalledProcessError

from BeautifulSoup import BeautifulSoup
import pexpect


def links_from_html(html):
    return [link.string.strip() for link in BeautifulSoup(html).findAll('a')]


class CommandEnvironment(object):
    DEFAULT_DEST = "/mnt"

    def __init__(self, chroot=None, src=None, dst=None):
        self.src = src
        self.dst = dst
        self.chroot = chroot
        self.__mounted = False
        self.__do_mount = False
        # We only perform a bind mount in the case where both
        # chroot and src have been set.
        if chroot and src:
            self.__do_mount = True
            if self.dst is None:
                self.dst = CommandEnvironment.DEFAULT_DEST
        else:
            self.dst = self.src

    @property
    def chroot_prefix(self):
        if self.chroot is None:
            return ''
        else:
            return "/usr/sbin/chroot {0} ".format(self.chroot)

    def _get_cmd(self, cmd):
        return self.chroot_prefix + cmd

    def call_with_expect(self, cmd, timeout=120):
        if isinstance(cmd, list):
            cmd = " ".join(cmd)
        expect = pexpect.spawn(self._get_cmd(cmd), timeout=timeout)
        # expect.logfile = os.devnull
        return expect

    def call(self, cmd, cwd=None):
        if isinstance(cmd, str):
            cmd = cmd.split(" ")
        if self.chroot_prefix:
            cmd = cmd.insert(0, self.chroot_prefix)
        try:
            if cwd:
                check_call(cmd, cwd=cwd)
            else:
                check_call(cmd)
        except CalledProcessError as err:
            raise Exception("Command {0} failed with status {1}".format(cmd, err.returncode))

    def mount(self):
        self.dst = dst
        cmd = ['mount', '--bind', self.src, self.dst]
        try:
            check_call(cmd)
        except CalledProcessError as err:
            raise Exception("Failed to bind mount {0} to {1}".format(self.src, self.dst))
        finally:
            self.__mounted = True

    def unmount(self):
        cmd = ['umount', self.dst]
        try:
            check_call(cmd)
        except CalledProcessError as err:
            raise Exception("Failed to unmount {0}".format(self.dst))
        finally:
            self.__mounted = False

    def __enter__(self):
        if self.__do_mount:
            self.mount()
	return self

    def __exit__(self, type=None, value=None, traceback=None):
        if self.__do_mount:
            self.unmount()
