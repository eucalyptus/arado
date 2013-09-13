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

from ConfigParser import SafeConfigParser

from .exception import ConfigError

__all__ = ['get_config']


class Config(SafeConfigParser):
    def __init__(self, config_file):
        SafeConfigParser.__init__(self)
        self.config_file = config_file
        self.read(config_file)

    def __getattr__(self, name):
        def _search_config(*args, **kwargs):
            if name not in ('general', 'paths', 'projects', 'mappings'):
                raise ConfigError("unknown category '{0}'".format(name))
            return dict((key, self.get(name, key))
                for key in self.options(name))
        return _search_config

    def __repr__(self):
        return '<config: {0}>'.format(self.config_file)

    def __str__(self):
        return super.__str__(self)

    @property
    def filename(self):
        return self.config_file

def get_config():
    if os.path.isfile('/etc/arado.conf'):
        return Config('/etc/arado.conf')
    elif os.path.isfile(os.path.join(os.getcwd(), 'arado.conf')):
        return Config(os.path.join(os.getcwd(), 'arado.conf'))
    elif os.path.isfile(os.path.expanduser('~/.arado.conf')):
        return Config((os.path.expanduser('~/.arado.conf')))
    else:
        raise Exception("no config file found!")

