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

from swift.common.middleware.s3api.subresource import BucketPolicy,\
    Statement, Principal

from swift.common.swob import Request, HTTPNotFound, HTTPNoContent
from swift.common.utils import json
from test.unit.common.middleware.s3api.test_s3_acl import \
    generate_s3acl_environ
from mock import patch


XMLNS_XSI = 'http://www.w3.org/2001/XMLSchema-instance'


class TestS3ApiBucketPolicy(S3ApiTestCase):

    def setUp(self):
        super(TestS3ApiBucketPolicy, self).setUp()

        self.s3api.conf.s3_acl = True
        self.swift.s3_acl = True

        self.account = 'test'
        owner_name = '%s:tester' % self.account
        self.default_owner = Owner(owner_name, owner_name)
        generate_s3acl_environ(self.account, self.swift, self.default_owner,
                               True)

    def tearDown(self):
        self.s3api.conf.s3_acl = False

    def _test_bucket_policy_GET(self, account):
        self.swift.register('GET', '/v1/AUTH_test/bucket', HTTPNoContent,
                            {"bucket_policy": None}, None)
        req = Request.blank('/bucket?policy',
                            environ={'REQUEST_METHOD': 'GET'},
                            headers={'Authorization': 'AWS %s:hmac' % account,
                                     'Date': self.get_date_header()})
        return self.call_s3api(req)

    def test_policy_without_target_bucket(self):
        # without target bucket
        req = Request.blank('/nobucket?policy',
                            environ={'REQUEST_METHOD': 'GET'},
                            headers={'Authorization': 'AWS test:tester:hmac',
                                     'Date': self.get_date_header()})
        with patch(
                'swift.common.middleware.s3api.s3request.get_container_info',
                lambda env, app, swift_source: {'status': 404}):
            self.swift.register('HEAD', '/v1/AUTH_test/nobucket',
                                HTTPNotFound, {}, None)
            status, headers, body = self.call_s3api(req)
        self.assertEqual(self._get_error_code(body), 'NoSuchBucket')

    def test_bucket_policy_GET_without_permission(self):
        status, headers, body = self._test_bucket_policy_GET('test:other')
        self.assertEqual(self._get_error_code(body), 'AccessDenied')

    def test_bucket_policy_GET_with_owner_permission(self):
        status, headers, body = self._test_bucket_policy_GET('test:tester')
        self.assertEqual(status.split()[0], '200')

    def _test_bucket_policy_PUT(self, account, bucket_policy):
        req = Request.blank('/bucket?policy',
                            environ={'REQUEST_METHOD': 'PUT'},
                            headers={'Authorization': 'AWS %s:hmac' % account,
                                     'Date': self.get_date_header()},
                            body=json.dumps(bucket_policy.to_dict()))

        return self.call_s3api(req)

    def _prepare_bucket_policy_statements(self):
        stmt = Statement(None, "Allow", Principal("*"), "s3:GetObject",
                         "arn:aws:s3:::bp-root/*", None)
        bucket_policy = BucketPolicy(None, "2020-04-06", [stmt])
        return bucket_policy

    def test_bucket_policy_PUT_without_permission(self):
        status, headers, body = \
            self._test_bucket_policy_PUT(
                'test:other',
                self._prepare_bucket_policy_statements())
        self.assertEqual(self._get_error_code(body), 'AccessDenied')

    def test_bucket_policy_PUT_with_fullcontrol_permission(self):
        status, headers, body = \
            self._test_bucket_policy_PUT(
                'test:tester',
                self._prepare_bucket_policy_statements())
        self.assertEqual(status.split()[0], '200')

    def test_bucket_policy_PUT_with_owner_permission(self):
        status, headers, body = \
            self._test_bucket_policy_PUT(
                'test:tester',
                self._prepare_bucket_policy_statements())
        self.assertEqual(status.split()[0], '200')

    def test_empty_json(self):
        req = Request.blank('/bucket?policy',
                            environ={'REQUEST_METHOD': 'PUT'},
                            headers={'Authorization': 'AWS test:tester:hmac',
                                     'Date': self.get_date_header()},
                            body='{}')
        status, headers, body = self.call_s3api(req)
        self.assertEqual(self._get_error_code(body), 'MalformedPolicy')

    def test_invalid_json(self):
        req = Request.blank('/bucket?policy',
                            environ={'REQUEST_METHOD': 'PUT'},
                            headers={'Authorization': 'AWS test:tester:hmac',
                                     'Date': self.get_date_header()},
                            body='invalid')
        status, headers, body = self.call_s3api(req)
        self.assertEqual(self._get_error_code(body), 'MalformedPolicy')

    def test_bucket_policy_DELETE(self):
        req = Request.blank('/bucket?policy',
                            environ={'REQUEST_METHOD': 'DELETE'},
                            headers={'Authorization': 'AWS test:tester:hmac',
                                     'Date': self.get_date_header()})
        status, headers, body = self.call_s3api(req)
        self.assertEqual(status.split()[0], '200')


class TestS3ApiNoSuchBucketPolicy(S3ApiTestCase):

    def setUp(self):
        super(TestS3ApiNoSuchBucketPolicy, self).setUp()

        self.s3api.conf.s3_acl = True
        self.swift.s3_acl = True

        self.account = 'test'
        owner_name = '%s:tester' % self.account
        self.default_owner = Owner(owner_name, owner_name)
        generate_s3acl_environ(self.account, self.swift, self.default_owner,
                               False)

    def tearDown(self):
        self.s3api.conf.s3_acl = False

    def test_bucket_policy_GET_error(self):
        req = Request.blank('/bucket?policy',
                            environ={'REQUEST_METHOD': 'GET'},
                            headers={'Authorization': 'AWS test:tester:hmac',
                                     'Date': self.get_date_header()})
        status, headers, body = self.call_s3api(req)
        self.assertEqual(status.split()[0], '404')
        self.assertEqual(self._get_error_code(body), 'NoSuchBucketPolicy')

    def test_bucket_policy_DELETE_error(self):
        req = Request.blank('/bucket?policy',
                            environ={'REQUEST_METHOD': 'DELETE'},
                            headers={'Authorization': 'AWS test:tester:hmac',
                                     'Date': self.get_date_header()})
        status, headers, body = self.call_s3api(req)
        self.assertEqual(status.split()[0], '404')
        self.assertEqual(self._get_error_code(body), 'NoSuchBucketPolicy')


if __name__ == '__main__':
    unittest.main()
