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
"""
------------
Acl Handlers
------------

Why do we need this
^^^^^^^^^^^^^^^^^^^

To make controller classes clean, we need these handlers.
It is really useful for customizing acl checking algorithms for
each controller.

Basic Information
^^^^^^^^^^^^^^^^^

BaseAclHandler wraps basic Acl handling.
(i.e. it will check acl from ACL_MAP by using HEAD)

How to extend
^^^^^^^^^^^^^

Make a handler with the name of the controller.
(e.g. BucketAclHandler is for BucketController)
It consists of method(s) for actual S3 method on controllers as follows.

Example::

   class BucketAclHandler(BaseAclHandler):
       def PUT:
           << put acl handling algorithms here for PUT bucket >>

.. note::
  If the method DON'T need to recall _get_response in outside of
  acl checking, the method have to return the response it needs at
  the end of method.

"""
from swift.common.middleware.s3api.subresource import ACL, Owner, encode_acl
from swift.common.middleware.s3api.s3response import MissingSecurityHeader, \
    MalformedACLError, UnexpectedContent, AccessDenied
from swift.common.middleware.s3api.etree import fromstring, XMLSyntaxError, \
    DocumentInvalid
from swift.common.middleware.s3api.utils import MULTIUPLOAD_SUFFIX, \
    sysmeta_header


def get_bucket_policy_handler(controller_name):
    return BaseBucketPolicyHandler


class BaseBucketPolicyHandler(object):
    """
    BaseBucketPolicyHandler: Handling bucket policy for basic requests
    """
    def __init__(self, req, logger, container=None, headers=None):
        self.req = req
        self.container = req.container_name if container is None else container
        self.method = req.environ['REQUEST_METHOD']
        self.user_id = self.req.user_id
        self.logger = logger

    def handle_policy(self, app, method, container=None):
        pass

    def _handle_policy(self, app, sw_method, container=None, obj=None,
                    permission=None, headers=None):
        pass

