# Copyright (c) 2014 OpenStack Foundation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from six.moves.urllib.parse import quote
from swift.common.utils import public

from swift.common.middleware.s3api.controllers.base import Controller, S3NotImplemented
from swift.common.middleware.s3api.s3response import NoSuchTagSetError
from swift.common.middleware.s3api.etree import tostring


class S3AclController(Controller):
    """
    Handles the following APIs:

    * GET Bucket acl
    * PUT Bucket acl
    * GET Object acl
    * PUT Object acl

    Those APIs are logged as ACL operations in the S3 server log.
    """
    @public
    def GET(self, req):
        """
        Handles GET Bucket acl and GET Object acl.
        """
        raise NoSuchTagSetError

    @public
    def PUT(self, req):
        """
        Handles PUT Bucket acl and PUT Object acl.
        """
        raise S3NotImplemented('Object tagging is not supported.')