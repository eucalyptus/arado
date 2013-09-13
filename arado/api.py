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
import re
import sys

# Third party libraries
import requests

# Local libraries
from .config import get_config
from .exception import PromotionError
from .utils import links_from_html


class PathBuilder(object):
    SOURCE_RE = re.compile('http://[\w\-\.]+/(.*)/centos/6/x86_64') 
    DEFAULT_OPTS = {
        "api": None,
        "buildtype": None,
        "release": None
    }

    def __init__(self, **opts):
        self.opts = dict(PathBuilder.DEFAULT_OPTS, **opts)
        self.api = self.opts.get('api')
        self.buildtype = self.opts.get('buildtype')
        self.release = self.opts.get('release')
        self.config = get_config()

    @property
    def mapping(self):
        try:
            return self.config.mappings().get(self.api.project)
        except:
            return None

    @property
    def source_path(self):
        path = self.SOURCE_RE.match(self.api.repository).groups()[0]
        return os.path.join(self.config.paths().get('source'), path)

    @property
    def dest_path(self):
        if self.buildtype and self.buildtype != 'release':
            return os.path.join(self.config.paths().get('destination'),
                    self.mapping, self.buildtype, self.release)
        else:
            return os.path.join(self.config.paths().get('destination'),
                    self.mapping, self.release)


class APIWrapper(object):
    API_TEMPL = "{0}?distro=centos&releasever=6&arch=x86_64&url={1}&ref={2}&allow-old=true"

    def __init__(self, project, commit):
        self.project = project
        self.commit = commit
        self.config = get_config()
        self.cached_packages = None

    @property
    def url(self):
        try:
            return self.config.projects().get(self.project)
        except:
            return None

    @property
    def api(self):
        try:
            return self.config.general().get('api-url')
        except:
            return None

    @property
    def repository(self):
        r = requests.get(APIWrapper.API_TEMPL.format(self.api, self.url, self.commit))
        if r.status_code != 200:
            raise PromotionError(r.text)
        return r.text.rstrip()

    @property
    def packages(self):
        try:
            if not self.cached_packages:
                r = requests.get(self.repository + "?F=0&P=*.rpm")
                if r.status_code != 200:
                    raise PromotionError(r.text)
                # Store list and remove the first item since
                # it is parent directory
                self.cached_packages = links_from_html(r.text)[1:]
            return self.cached_packages
        except Exception as err:
            print("exception: {0}".format(err)) 
            return []
