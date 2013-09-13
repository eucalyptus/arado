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
import tempfile
from subprocess import check_call, CalledProcessError

# Third party libraries
import jinja2

# Local libraries
from .signing import export_public_key_file
from .util import SigningError

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'data')


class TemplateFile(object):
    def __init__(self, template, path, **opts):
        self.loader = jinja2.loaders.FileSystemLoader(path)
        self.env = jinja2.Environment(loader=self.loader)
        self.opts = opts
        self.template = template

    def __str__(self):
        for key, value in self.opts.iteritems():
            if value is None:
                raise ValueError("Required key '{}' is not set".format(key))
        tmpl = self.env.select_template([self.template])
        return tmpl.render(**self.opts)


class SpecFile(TemplateFile):
    def __init__(self, path, **opts):
        super(SpecFile, self).__init__('spec.tmpl', path, **opts)


class RepoFile(TemplateFile):
    def __init__(self, path, **opts):
        super(RepoFile, self).__init__('repo.tmpl', path, **opts)


class PackageBuilder(object):
    DEFAULT_OPTS = {
        'url': None,
        'key_name': None,
        'package_name': None,
        'package_version': None,
        'release_version': None,
        'platform': '.el6',
        'pubkey': False,
        'repofile': False,
        'cert': False,
        'key': False,
    }

    def __init__(self, **opts):
        self.opts = dict(PackageBuilder.DEFAULT_OPTS, **opts)
        self.path = TEMPLATE_PATH

    @staticmethod
    def create_rpm_dir():
        tmpdir = tempfile.mkdtemp()
        for d in ('RPMS', 'SPECS', 'SOURCES', 'BUILD'):
            os.makedirs(os.path.join(tmpdir, d))
        return tmpdir

    def build(self):
        self.opts["rpmdir"] = PackageBuilder.create_rpm_dir()

        # Export public key
        self.opts["pubkey"] = tempfile.mktemp(suffix=".pub",
            dir=os.path.join(self.opts["rpmdir"], "SOURCES"))
        export_public_key_file(self.opts["key_name"],
            self.opts["pubkey"])

        # Generate repo file from template
        self.opts["repofile"] = tempfile.mktemp(suffix=".repo",
            dir=os.path.join(self.opts["rpmdir"], "SOURCES"))
        self.repofile = RepoFile(self.path, **self.opts)
        with open(self.opts["repofile"], "wb") as fp:
            fp.write(str(self.repofile))

        # Generate spec file from template
        tmpspec = tempfile.mktemp(suffix=".spec",
            dir=os.path.join(self.opts["rpmdir"], "SPECS"))
        self.specfile = SpecFile(self.path, **self.opts)
        with open(tmpspec, "wb") as fp:
            write(str(self.specfile))

        cmd = [ '/usr/bin/rpmbuild', '-bb', tmpspec ]
        try:
            subprocess.check_call(cmd)
        except CalledProcessError as err:
            raise Exception("ERROR: command {0} failed with status {1}".format(cmd, err.returncode))

        return glob.glob(os.path.join(self.opts["rpmdir"],
            "RPMS/noarch/*.rpm"))[0]
