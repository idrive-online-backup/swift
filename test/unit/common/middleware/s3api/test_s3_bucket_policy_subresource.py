import unittest
from swift.common.middleware.s3api.subresource import BucketPolicy,\
    Statement, Principal, encode_bucket_policy, decode_bucket_policy, sysmeta_header
from swift.common.utils import json
from swift.common.middleware.s3api.s3response import AccessDenied


class TestS3ApiBucketPolicySubResource(unittest.TestCase):

    def test_bucket_policy_from_dict_undefined(self):
        for policy_dict in [None, {}]:
            with self.assertRaises(AttributeError) as context:
                BucketPolicy.from_dict(policy_dict)

    def test_bucket_policy_from_dict_malformed_json(self):
        policy_dict = {
            "Version": "2020-04-06",
            "Statement": [
                {
                    "Effect": "Allow",
                }
            ]
        }
        with self.assertRaises(AttributeError) as context:
            BucketPolicy.from_dict(policy_dict)

    def test_bucket_policy_from_dict(self):
        policy_dict1 = {
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::MyBucket/*"
                },
                {
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::MyBucket/MySecretFolder/*"
                },
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "arn:aws:iam::123456789012:root"
                    },
                    "Action": [
                        "s3:DeleteObject",
                        "s3:PutObject"
                    ],
                    "Resource": "arn:aws:s3:::MyBucket/*"
                }
            ]
        }
        policy_dict2 = {

            "Version": "2012-10-17",

            "Statement": [

                {

                    "Sid": "AddCannedAcl",

                    "Effect": "Allow",

                    "Principal": {

                        "AWS": [

                            "arn:aws:iam::100000000164:root",

                            "arn:aws:iam::100000000162:root"

                        ]

                    },

                    "Action": [

                        "s3:GetObject",

                        "s3:ListBucket",

                        "s3:PutObject",

                        "s3:PutObjectAcl"

                    ],

                    "Resource": "arn:aws:s3:::multi-account/*"

                }

            ]

        }
        policy_dict3 = {

            "Id": "S3PolicyId1",

            "Version": "2012-10-17",

            "Statement": [

                {

                    "Sid": "IPAllow",

                    "Effect": "Allow",

                    "Principal": {

                        "AWS": "*"

                    },

                    "Action": "s3:*",

                    "Resource": "arn:aws:s3:::vbatra-ip-only/*",

                    "Condition": {

                        "IpAddress": {

                            "aws:SourceIp": "77.19.132.0/24"

                        },

                        "NotIpAddress": {

                            "aws:SourceIp": "76.19.132.120/32"

                        }

                    }

                }

            ]

        }
        for input_json in [policy_dict1, policy_dict2, policy_dict3]:
            bucket_policy = BucketPolicy.from_dict(input_json)
            self.assertIsInstance(bucket_policy, BucketPolicy)
            self.assertIsInstance(bucket_policy.statement[0], Statement)
            if input_json.get("Version"):
                self.assertEqual(bucket_policy.version, input_json["Version"])
            if input_json.get("Id"):
                self.assertEqual(bucket_policy.id, input_json["Id"])

    def test_bucket_policy_to_dict(self):
        policy_dict = {
           "Version":"2020-04-06",
           "Statement":[
              {
                 "Effect":"Allow",
                 "Principal":{
                    "AWS":"*"
                 },
                 "Action":"s3:GetObject",
                 "Resource":[
                    "arn:aws:s3:::bp-root/*"
                 ]
              }
           ]
        }
        bp = BucketPolicy.from_dict(policy_dict)
        policy_dict_from_dict = bp.to_dict()
        self.assertDictEqual(policy_dict_from_dict, policy_dict)

    def test_decode_bucket_policy(self):
        access_control_policy = {
           "Version":"2020-04-06",
           "Statement":[
              {
                 "Effect":"Allow",
                 "Principal":{
                    "AWS":"*"
                 },
                 "Action":"s3:GetObject",
                 "Resource":[
                    "arn:aws:s3:::bp-root/*"
                 ]
              }
           ]
        }
        headers = {sysmeta_header('bucket', 'policy'):
                       json.dumps(access_control_policy)}
        bucket_policy = decode_bucket_policy(headers, True)
        self.assertIsInstance(bucket_policy,  BucketPolicy)
        self.assertEqual("2020-04-06", bucket_policy.version)
        self.assertIsInstance(bucket_policy.statement[0], Statement)
        self.assertEqual(bucket_policy.statement[0].effect, "Allow")
        self.assertIsInstance(bucket_policy.statement[0].principal, Principal)
        self.assertEqual(bucket_policy.statement[0].principal.aws, "*")
        self.assertEqual(bucket_policy.statement[0].action, "s3:GetObject")
        self.assertIsInstance(bucket_policy.statement[0].resource, list)
        self.assertEqual(bucket_policy.statement[0].resource[0], "arn:aws:s3:::bp-root/*")

    def test__encode_bucket_policy(self):
        stmt = Statement(None, "Allow", Principal("*"), "s3:GetObject", "arn:aws:s3:::bp-root/*", None)
        bucket_policy = BucketPolicy(None, "2020-04-06", [stmt])
        encoded_bucket_policy_headers = encode_bucket_policy(bucket_policy)
        header_value = json.loads(encoded_bucket_policy_headers[sysmeta_header('bucket', 'policy')])
        self.assertEqual(header_value["Version"], "2020-04-06")
        self.assertEqual(header_value["Statement"][0]["Effect"], "Allow")
        self.assertEqual(header_value["Statement"][0]["Principal"]["AWS"], "*")
        self.assertEqual(header_value["Statement"][0]["Action"], "s3:GetObject")
        self.assertEqual(header_value["Statement"][0]["Resource"], "arn:aws:s3:::bp-root/*")
        self.assertEqual(header_value["Statement"][0]["Action"], "s3:GetObject")

    def test_user_action(self):
        resp = BucketPolicy.user_action("object", "GET")
        self.assertEqual("s3:GetObject", resp)
        resp = BucketPolicy.user_action("object", "PUT")
        self.assertEqual("s3:PutObject", resp)
        resp = BucketPolicy.user_action("object", "PUT", "ACL")
        self.assertEqual("s3:PutObjectAcl", resp)
        resp = BucketPolicy.user_action("container", "PUT")
        self.assertEqual("s3:CreateBucket", resp)
        resp = BucketPolicy.user_action("container", "GET")
        self.assertEqual("s3:ListBucket", resp)
        resp = BucketPolicy.user_action("container", "DELETE")
        self.assertEqual("s3:DeleteBucket", resp)
        resp = BucketPolicy.user_action("container", "GET", "ACL")
        self.assertEqual("s3:ListBucketAcl", resp)

    def check_owner(self, bucket_policy, user_id, owner_id):
        try:
            bucket_policy.check_owner(user_id, owner_id)
            return True
        except AccessDenied:
            return False

    def test_bucket_policy_check_owner(self):
        bp = BucketPolicy(None,None, None, None)
        bp.s3_acl = True
        result = self.check_owner(bp, "test:tester", None)
        self.assertFalse(result)
        bp.allow_no_owner = True
        result = self.check_owner(bp, "test:tester", None)
        self.assertTrue(result)
        result = self.check_owner(bp, "test:tester", "test:tester")
        self.assertTrue(result)
        result = self.check_owner(bp, "test:tester", "test:tester2")
        self.assertFalse(result)

    def test_bucket_policy_match_action(self):
        res = BucketPolicy.match_action("*", "s3:GetObject")
        self.assertTrue(res)
        res = BucketPolicy.match_action(["s3:GetObject", "s3:PutObject"], "s3:ListBucket")
        self.assertFalse(res)

    def test_bucket_policy_match_principal(self):
        res = BucketPolicy.match_principal("test:tester", "*")
        self.assertTrue(res)
        principal = Principal("arn:aws:iam::test:tester")
        res = BucketPolicy.match_principal("test:tester", principal)
        self.assertTrue(res)
        res = BucketPolicy.match_principal("test:tester1", principal)
        self.assertFalse(res)

    def test_match_resource(self):
        res = BucketPolicy.match_resource(["arn:aws:s3:::bucket/*"], "bucket", "object")
        self.assertTrue(res)
        res = BucketPolicy.match_resource(["arn:aws:s3:::bucket/*"], "invalid", "object")
        self.assertFalse(res)


if __name__ == '__main__':
    unittest.main()