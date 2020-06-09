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


class ObjectTaggingController(Controller):
    """
    Handles the following APIs:

    * GET Object tagging
    * PUT Object tagging
    * DELETE Object tagging

    """
    @public
    def GET(self, req):
        """
        Handles GET Object tagging.
        """
        raise NoSuchTagSetError

    @public
    def PUT(self, req):
        """
        Handles PUT Object tagging.
        """
        raise S3NotImplemented('Object tagging is not supported.')

    @public
    def DELETE(self, req):
        """
        Handles DELETE Object tagging.
        """
        raise S3NotImplemented('Object tagging is not supported.')