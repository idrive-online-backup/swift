# Copyright (c) 2014 OpenStack Foundation
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

import unittest
from test.unit.common.middleware.s3api.test_s3api import S3ApiTestCase
from swift.common.middleware.s3api.subresource import Owner


XMLNS_XSI = 'http://www.w3.org/2001/XMLSchema-instance'


class TestS3ApiBucketPolicy(S3ApiTestCase):

    def setUp(self):
        super(TestS3ApiBucketPolicy, self).setUp()

        self.s3api.conf.s3_acl = True
        self.swift.s3_acl = True

        account = 'test'
        owner_name = '%s:tester' % account
        self.default_owner = Owner(owner_name, owner_name)

    def tearDown(self):
        self.s3api.conf.s3_acl = False

if __name__ == '__main__':
    unittest.main()
