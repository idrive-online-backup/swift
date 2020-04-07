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

from swift.common.middleware.s3api.controllers.base import Controller
from swift.common.middleware.s3api.s3response import HTTPOk, NoSuchKey, NoSuchBucketPolicy


class S3BucketPolicyController(Controller):
    """
    Handles the following APIs:

    * GET Bucket Policy acl
    * PUT Bucket Policy acl

    """
    @public
    def GET(self, req):
        """
        Handles GET Bucket Policy.
        """

        resp = req.get_response(self.app)
        if hasattr(resp, "bucket_policy") and resp.bucket_policy:
            bucket_policy = resp.bucket_policy
            resp = HTTPOk()
            import json
            resp.body = json.dumps(bucket_policy.to_dict())
        else:
            raise NoSuchBucketPolicy

        return resp

    @public
    def PUT(self, req):
        """
        Handles PUT Bucket Policy.
        """
        req.get_response(self.app, 'POST')

        return HTTPOk()
