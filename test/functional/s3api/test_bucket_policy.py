# Copyright (c) 2015 OpenStack Foundation
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
import os
import test.functional as tf
import json
import botocore

from test.functional.s3api import S3ApiBase
from test.functional.s3api.s3_test_client import Connection, get_boto3_conn
from test.functional.s3api.utils import get_error_code


def setUpModule():
    tf.setup_package()


def tearDownModule():
    tf.teardown_package()


class TestS3BucketPolicy(S3ApiBase):
    def setUp(self):
        super(TestS3BucketPolicy, self).setUp()
        self.bucket = 'bucket'
        if 's3_access_key3' not in tf.config or \
                's3_secret_key3' not in tf.config:
            raise tf.SkipTest(
                'TestS3Acl requires s3_access_key3 and s3_secret_key3 '
                'configured for reduced-access user')
        status, headers, body = self.conn.make_request('PUT', self.bucket)
        self.assertEqual(status, 200, body)
        access_key3 = tf.config['s3_access_key3']
        secret_key3 = tf.config['s3_secret_key3']
        self.conn3 = Connection(access_key3, secret_key3, access_key3)
        if 's3_access_key2' not in tf.config or \
                's3_secret_key2' not in tf.config:
            raise tf.SkipTest(
                'TestS3Acl requires s3_access_key2 and s3_secret_key2 '
                'configured for reduced-access user')
        access_key2 = tf.config['s3_access_key2']
        secret_key2 = tf.config['s3_secret_key2']
        self.conn2 = Connection(access_key2, secret_key2, access_key2)

    def test_bucket_policy(self):
        self.conn.make_request('PUT', self.bucket, None)
        query = 'policy'

        policy_dict = {
            "Version": "2020-04-06",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "*"
                    },
                    "Action": "s3:GetObject",
                    "Resource": [
                        "arn:aws:s3:::bp-root/*"
                    ]
                }
            ]
        }


        # PUT Bucket Policy
        status, headers, body = \
            self.conn.make_request('PUT', self.bucket, body=json.dumps(policy_dict),
                                   query=query)
        self.assertEqual(status, 200)
        self.assertCommonResponseHeaders(headers)
        self.assertEqual(headers['content-length'], '0')

        # GET Bucket Policy
        status, headers, body = \
            self.conn.make_request('GET', self.bucket, query=query)
        self.assertEqual(status, 200)
        self.assertCommonResponseHeaders(headers)
        self.assertEqual(headers['content-length'], str(len(body)))
        self.assertTrue(headers['content-type'] is not None)
        bucket_poicy = json.loads(body)
        self.assertEqual(bucket_poicy, policy_dict)

        # DELETE Bucket Policy
        status, headers, body = \
            self.conn.make_request('DELETE', self.bucket, query=query)
        self.assertEqual(status, 200)
        self.assertCommonResponseHeaders(headers)
        self.assertEqual(headers['content-length'], str(len(body)))
        self.assertEqual(headers['content-length'], '0')

    def test_put_bucket_policy_error(self):
        aws_error_conn = Connection(aws_secret_key='invalid')
        status, headers, body = \
            aws_error_conn.make_request('PUT', self.bucket, query='policy')
        self.assertEqual(get_error_code(body), 'SignatureDoesNotMatch')

        status, headers, body = \
            self.conn.make_request('PUT', 'nothing', query='policy')
        self.assertEqual(get_error_code(body), 'NoSuchBucket')

        status, headers, body = \
            self.conn3.make_request('PUT', self.bucket, query='policy')
        self.assertEqual(get_error_code(body), 'AccessDenied')

        self.conn.make_request('PUT', self.bucket, None)
        malformed_policy = {
            "Version": "2020-04-06",
        }
        status, headers, body = \
            self.conn.make_request('PUT', self.bucket, body=json.dumps(malformed_policy),
                                   query='policy')
        self.assertEqual(get_error_code(body), 'MalformedPolicy')

        status, headers, body = \
            self.conn.make_request('PUT', self.bucket,
                                   query='policy')
        self.assertEqual(get_error_code(body), 'MissingRequestBodyError')


    def test_get_bucket_policy_error(self):
        aws_error_conn = Connection(aws_secret_key='invalid')
        status, headers, body = \
            aws_error_conn.make_request('GET', self.bucket, query='policy')
        self.assertEqual(get_error_code(body), 'SignatureDoesNotMatch')

        status, headers, body = \
            self.conn.make_request('GET', 'nothing', query='policy')
        self.assertEqual(get_error_code(body), 'NoSuchBucket')

        status, headers, body = \
            self.conn3.make_request('GET', self.bucket, query='policy')
        self.assertEqual(get_error_code(body), 'AccessDenied')

        status, headers, body = \
            self.conn.make_request('GET', self.bucket, query='policy')
        self.assertEqual(get_error_code(body), 'NoSuchBucketPolicy')

    def test_delete_bucket_policy_error(self):
        aws_error_conn = Connection(aws_secret_key='invalid')
        status, headers, body = \
            aws_error_conn.make_request('DELETE', self.bucket, query='policy')
        self.assertEqual(get_error_code(body), 'SignatureDoesNotMatch')

        status, headers, body = \
            self.conn.make_request('DELETE', 'nothing', query='policy')
        self.assertEqual(get_error_code(body), 'NoSuchBucket')

        status, headers, body = \
            self.conn3.make_request('DELETE', self.bucket, query='policy')
        self.assertEqual(get_error_code(body), 'AccessDenied')

        status, headers, body = \
            self.conn.make_request('DELETE', self.bucket, query='policy')
        self.assertEqual(get_error_code(body), 'NoSuchBucketPolicy')

    def test_bucket_policy_list_objects_key2(self):
        self.conn.make_request('PUT', self.bucket, None)
        conn2 = get_boto3_conn(tf.config['s3_access_key2'],
                               tf.config['s3_secret_key2'])
        with self.assertRaises(botocore.exceptions.ClientError) as ctx:
            conn2.list_objects(Bucket=self.bucket)
        self.assertEqual(
            ctx.exception.response['ResponseMetadata']['HTTPStatusCode'], 403)
        self.assertEqual(ctx.exception.response['Error']['Code'], 'AccessDenied')
        policy_dict = {
            "Version": "2020-04-06",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "*"
                    },
                    "Action": "s3:ListBucket",
                    "Resource": [
                        "arn:aws:s3:::{}/*".format(self.bucket)
                    ]
                }
            ]
        }
        status, headers, body = \
            self.conn.make_request('PUT', self.bucket, body=json.dumps(policy_dict),
                                   query="policy")
        self.assertEqual(status, 200)
        resp = conn2.list_objects(Bucket=self.bucket)
        self.assertEqual(200, resp['ResponseMetadata']['HTTPStatusCode'])

    def test_bucket_policy_put_object_key2(self):
        self.conn.make_request('PUT', self.bucket, None)
        obj = 'object'
        content = b'abc123'
        # PUT Object
        status, headers, body = \
            self.conn.make_request('PUT', self.bucket, obj, body=content)
        self.assertEqual(status, 200)
        status, headers, body = \
            self.conn.make_request('GET', self.bucket, obj)
        self.assertEqual(status, 200)

        status, headers, body = \
            self.conn2.make_request('PUT', self.bucket, obj, body=content)
        self.assertEqual(status, 403)
        policy_dict = {
            "Version": "2020-04-06",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "arn:aws:iam::test:tester2"
                    },
                    "Action": ["s3:PutObject"],
                    "Resource": [
                        "arn:aws:s3:::{}/*".format(self.bucket)
                    ]
                }
            ]
        }
        status, headers, body = \
            self.conn.make_request('PUT', self.bucket, body=json.dumps(policy_dict),
                                   query="policy")
        self.assertEqual(status, 200)
        status, headers, body = \
            self.conn2.make_request('PUT', self.bucket, obj, body=content)
        self.assertEqual(status, 200)

    def test_bucket_policy_get_object_key2(self):
        self.conn.make_request('PUT', self.bucket, None)
        obj = 'object'
        content = b'abc123'
        # PUT Object
        status, headers, body = \
            self.conn.make_request('PUT', self.bucket, obj, body=content)
        self.assertEqual(status, 200)
        status, headers, body = \
            self.conn.make_request('GET', self.bucket, obj)
        self.assertEqual(status, 200)

        status, headers, body = \
            self.conn2.make_request('GET', self.bucket, obj)
        self.assertEqual(status, 403)
        policy_dict = {
            "Version": "2020-04-06",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "arn:aws:iam::test:tester2"
                    },
                    "Action": ["s3:GetObject"],
                    "Resource": [
                        "arn:aws:s3:::{}/*".format(self.bucket)
                    ]
                }
            ]
        }
        status, headers, body = \
            self.conn.make_request('PUT', self.bucket, body=json.dumps(policy_dict),
                                   query="policy")
        self.assertEqual(status, 200)
        status, headers, body = \
            self.conn2.make_request('GET', self.bucket, obj)
        self.assertEqual(status, 200)

    def test_bucket_policy_delete_object_key2(self):
        self.conn.make_request('PUT', self.bucket, None)
        obj = 'object'
        content = b'abc123'
        # PUT Object
        status, headers, body = \
            self.conn.make_request('PUT', self.bucket, obj, body=content)
        self.assertEqual(status, 200)

        status, headers, body = \
            self.conn2.make_request('DELETE', self.bucket, obj)
        self.assertEqual(status, 403)
        policy_dict = {
            "Version": "2020-04-06",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "arn:aws:iam::test:tester2"
                    },
                    "Action": ["s3:DeleteObject"],
                    "Resource": [
                        "arn:aws:s3:::{}/{}".format(self.bucket, obj)
                    ]
                }
            ]
        }
        status, headers, body = \
            self.conn.make_request('PUT', self.bucket, body=json.dumps(policy_dict),
                                   query="policy")
        self.assertEqual(status, 200)
        status, headers, body = \
            self.conn2.make_request('DELETE', self.bucket, obj)
        self.assertEqual(status, 204)


class TestS3AclSigV4(TestS3BucketPolicy):
    @classmethod
    def setUpClass(cls):
        os.environ['S3_USE_SIGV4'] = "True"

    @classmethod
    def tearDownClass(cls):
        del os.environ['S3_USE_SIGV4']

    def setUp(self):
        super(TestS3AclSigV4, self).setUp()


if __name__ == '__main__':
    unittest.main()
