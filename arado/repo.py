# Software License Agreement (BSD License)
#
# Copyright (c) 2012, Eucalyptus Systems, Inc.
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

import requests
import os
import sys
from .exception import PromotionError
from .aradoutil import parsefiles


class PathBuilder(object):
    SRC_PATH = "/srv/build-repo/repository/release"
    DEST_PATH = "/srv/software/releases"
    PATH_MAP = {
        "eucalyptus" : "eucalyptus",
        "enterprise" : "enterprise",
        "eucadw" : "eucalyptus",
        "eucalyptus-console" : "eucalyptus",
    }

    def __init__(self, api, buildtype=None):
        self.api = api
        self.buildtype = buildtype

    @property
    def project_path(self):
        try:
            return PathBuilder.PATH_MAP[self.api.project]
        except:
            return None

    @property
    def source_path(self):
        return os.path.join(PathBuilder.SRC_PATH,
                self.api.repository.replace("http://" + APIWrapper.API_SERVER + "/", "")
                        .replace("/centos/6/x86_64", ""))

    @property
    def dest_path(self):
        if self.buildtype and self.buildtype is not "release":
            return os.path.join(PathBuilder.DEST_PATH, self.project_path,
                    self.buildtype, self.api.release)
        else:
            return os.path.join(PathBuilder.DEST_PATH, self.project_path,
                    self.api.release)


class APIWrapper(object):
    API_SERVER = "packages.release.eucalyptus-systems.com"
    API_TEMPL = "http://%s/api/1/genrepo?distro=centos&releasever=6&arch=x86_64&url=%s&ref=%s&allow-old=true"
    REPO_MAP = {
        "eucalyptus" : "repo-euca@git.eucalyptus-systems.com:eucalyptus",
        "enterprise" : "repo-euca@git.eucalyptus-systems.com:internal",
        "eucadw" : "https://github.com/eucalyptus/bodega.git",
        "eucalyptus-console" : "https://github.com/eucalyptus/eucalyptus-ui.git",
    }

    def __init__(self, project, commit, release=None):
        self.project = project
        self.commit = commit
        self.release = release
        self.cached_packages = None

    @property
    def url(self):
        try:
            return APIWrapper.REPO_MAP[self.project]
        except:
            return None

    @property
    def repository(self):
        r = requests.get(APIWrapper.API_TEMPL % (APIWrapper.API_SERVER, self.url, self.commit))
        if r.status_code != 200:
            raise PromotionError, r.text
        return r.text.rstrip()

    @property
    def packages(self):
        try:
            if not self.cached_packages:
                r = requests.get(self.repository + "?F=0&P=*.rpm")
                if r.status_code != 200:
                    raise PromotionError, r.text
                # Store list and remove the first item since it is parent directory
                self.cached_packages = parsefiles(r.text)[1:]
            return self.cached_packages
        except Exception:
            return []

