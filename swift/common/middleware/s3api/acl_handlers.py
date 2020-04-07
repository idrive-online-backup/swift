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
from swift.common.middleware.s3api.subresource import ACL, Owner, encode_acl, BucketPolicy
from swift.common.middleware.s3api.s3response import MissingSecurityHeader, \
    MalformedACLError, UnexpectedContent, AccessDenied
from swift.common.middleware.s3api.etree import fromstring, XMLSyntaxError, \
    DocumentInvalid
from swift.common.middleware.s3api.utils import MULTIUPLOAD_SUFFIX, \
    sysmeta_header
import json


def get_acl_handler(controller_name):
    print(controller_name)
    for base_klass in [BucketPolicyHandler, MultiUploadAclHandler]:
        # pylint: disable-msg=E1101
        for handler in base_klass.__subclasses__():
            handler_suffix_len = len('AclHandler') \
                if not handler.__name__ == 'S3AclHandler' and \
                   not handler.__name__ == 'S3BucketPolicyHandler' else len('Handler')
            if handler.__name__[:-handler_suffix_len] == controller_name:
                return handler
    return BucketPolicyHandler


class BaseAclHandler(object):
    """
    BaseAclHandler: Handling ACL for basic requests mapped on ACL_MAP
    """
    def __init__(self, req, logger, container=None, obj=None, headers=None):
        self.req = req
        self.container = req.container_name if container is None else container
        self.obj = req.object_name if obj is None else obj
        self.method = req.environ['REQUEST_METHOD']
        self.user_id = self.req.user_id
        self.headers = req.headers if headers is None else headers
        self.logger = logger

    def request_with(self, container, obj, headers):
        self.logger.debug("type(self) %s", type(self))
        return type(self)(self.req, self.logger,
                          container=container, obj=obj, headers=headers)

    def handle_acl(self, app, method, container=None, obj=None, headers=None):
        method = method or self.method
        self.logger.debug("method %s", method)
        ah = self.request_with(container, obj, headers)
        self.logger.debug("ah %s", ah)
        self.logger.debug("hasattr(ah, method) %s", hasattr(ah, method))
        self.logger.debug("getattr(ah, method) %s", getattr(ah, method))
        self.logger.debug("app %s", app)
        if hasattr(ah, method):
            return getattr(ah, method)(app)
        else:
            return ah._handle_acl(app, method)

    def _handle_acl(self, app, sw_method, container=None, obj=None,
                    permission=None, headers=None):
        """
        General acl handling method.
        This method expects to call Request._get_response() in outside of
        this method so that this method returns response only when sw_method
        is HEAD.
        """

        container = self.container if container is None else container
        obj = self.obj if obj is None else obj
        sw_method = sw_method or self.req.environ['REQUEST_METHOD']
        resource = 'object' if obj else 'container'
        headers = self.headers if headers is None else headers

        self.logger.debug(
            'checking permission: %s %s %s %s' %
            (container, obj, sw_method, dict(headers)))

        if not container:
            return

        if not permission and (self.method, sw_method, resource) in ACL_MAP:
            acl_check = ACL_MAP[(self.method, sw_method, resource)]
            resource = acl_check.get('Resource') or resource
            permission = acl_check['Permission']

        if not permission:
            self.logger.debug(
                '%s %s %s %s' % (container, obj, sw_method, headers))
            raise Exception('No permission to be checked exists')

        if resource == 'object':
            version_id = self.req.params.get('versionId')
            if version_id is None:
                query = {}
            else:
                query = {'version-id': version_id}
            resp = self.req.get_acl_response(app, 'HEAD',
                                             container, obj,
                                             headers, query=query)
            acl = resp.object_acl
        elif resource == 'container':
            resp = self.req.get_acl_response(app, 'HEAD',
                                             container, '')
            self.logger.debug("resp %s", resp)
            acl = resp.bucket_acl
            self.logger.debug("setting bucket policy in response")
            if hasattr(resp, 'bucket_policy'):
                policy = resp.bucket_policy

        try:
            acl.check_permission(self.user_id, permission)
        except Exception as e:
            self.logger.debug(acl)
            self.logger.debug('permission denined: %s %s %s' %
                              (e, self.user_id, permission))
            raise

        if sw_method == 'HEAD':
            return resp

    def get_acl(self, headers, body, bucket_owner, object_owner=None):
        """
        Get ACL instance from S3 (e.g. x-amz-grant) headers or S3 acl xml body.
        """
        acl = ACL.from_headers(headers, bucket_owner, object_owner,
                               as_private=False)

        if acl is None:
            # Get acl from request body if possible.
            if not body:
                raise MissingSecurityHeader(missing_header_name='x-amz-acl')
            try:
                elem = fromstring(body, ACL.root_tag)
                acl = ACL.from_elem(
                    elem, True, self.req.allow_no_owner)
            except(XMLSyntaxError, DocumentInvalid):
                raise MalformedACLError()
            except Exception as e:
                self.logger.error(e)
                raise
        else:
            if body:
                # Specifying grant with both header and xml is not allowed.
                raise UnexpectedContent()

        return acl


class BucketPolicyHandler(BaseAclHandler):

    def __init__(self, req, logger, container=None, obj=None, headers=None):
        super(BucketPolicyHandler, self).__init__(req, logger, container, obj, headers)

    def get_bucket_policy(self, body):
        """
        Get BucketPolicy instance json body.
        """
        self.logger.debug("body %s", body)
        self.logger.debug("body %s", type(body))
        try:
            import json
            policy = BucketPolicy.from_dict(json.loads(body))
        except Exception as e:
            self.logger.error(e)
            raise
        return policy

    # def _handle_acl(self, app, sw_method, container=None, obj=None,
    #                 permission=None, headers=None):
    #     super(self)._handle_acl(app, sw_method, container, obj, permission, headers)


class BucketAclHandler(BucketPolicyHandler):
    """
    BucketAclHandler: Handler for BucketController
    """
    def DELETE(self, app):
        if self.container.endswith(MULTIUPLOAD_SUFFIX):
            # anyways, delete multiupload container doesn't need acls
            # because it depends on GET segment container result for
            # cleanup
            pass
        else:
            return self._handle_acl(app, 'DELETE')

    def HEAD(self, app):
        if self.method == 'DELETE':
            return self._handle_acl(app, 'DELETE')
        else:
            return self._handle_acl(app, 'HEAD')

    def GET(self, app):
        if self.method == 'DELETE' and \
                self.container.endswith(MULTIUPLOAD_SUFFIX):
            pass
        else:
            return self._handle_acl(app, 'GET')

    def PUT(self, app):
        req_acl = ACL.from_headers(self.req.headers,
                                   Owner(self.user_id, self.user_id))

        if not self.req.environ.get('swift_owner'):
            raise AccessDenied()

        # To avoid overwriting the existing bucket's ACL, we send PUT
        # request first before setting the ACL to make sure that the target
        # container does not exist.
        self.req.get_acl_response(app, 'PUT', self.container)

        # update metadata
        self.req.bucket_acl = req_acl

        # FIXME If this request is failed, there is a possibility that the
        # bucket which has no ACL is left.
        return self.req.get_acl_response(app, 'POST')


class ObjectAclHandler(BucketPolicyHandler):
    """
    ObjectAclHandler: Handler for ObjectController
    """
    def HEAD(self, app):
        # No check object permission needed at DELETE Object
        if self.method != 'DELETE':
            return self._handle_acl(app, 'HEAD')

    def PUT(self, app):
        b_resp = self._handle_acl(app, 'HEAD', obj='')
        req_acl = ACL.from_headers(self.req.headers,
                                   b_resp.bucket_acl.owner,
                                   Owner(self.user_id, self.user_id))
        self.req.object_acl = req_acl


class S3AclHandler(BucketPolicyHandler):
    """
    S3AclHandler: Handler for S3AclController
    """
    def GET(self, app):
        self._handle_acl(app, 'HEAD', permission='READ_ACP')

    def PUT(self, app):
        if self.req.is_object_request:
            b_resp = self.req.get_acl_response(app, 'HEAD', obj='')
            o_resp = self._handle_acl(app, 'HEAD', permission='WRITE_ACP')
            req_acl = self.get_acl(self.req.headers,
                                   self.req.xml(ACL.max_xml_length),
                                   b_resp.bucket_acl.owner,
                                   o_resp.object_acl.owner)

            # Don't change the owner of the resource by PUT acl request.
            o_resp.object_acl.check_owner(req_acl.owner.id)

            for g in req_acl.grants:
                self.logger.debug(
                    'Grant %s %s permission on the object /%s/%s' %
                    (g.grantee, g.permission, self.req.container_name,
                     self.req.object_name))
            self.req.object_acl = req_acl
        else:
            self._handle_acl(app, self.method)

    def POST(self, app):
        if self.req.is_bucket_request:
            resp = self._handle_acl(app, 'HEAD', permission='WRITE_ACP')

            req_acl = self.get_acl(self.req.headers,
                                   self.req.xml(ACL.max_xml_length),
                                   resp.bucket_acl.owner)

            # Don't change the owner of the resource by PUT acl request.
            resp.bucket_acl.check_owner(req_acl.owner.id)

            for g in req_acl.grants:
                self.logger.debug(
                    'Grant %s %s permission on the bucket /%s' %
                    (g.grantee, g.permission, self.req.container_name))
            self.req.bucket_acl = req_acl
        else:
            self._handle_acl(app, self.method)


class S3BucketPolicyHandler(BucketPolicyHandler):

    def GET(self, app):
        self._handle_acl(app, 'HEAD', permission='READ_ACP')

    def POST(self, app):
        resp = self._handle_acl(app, 'HEAD')
        self.logger.debug("resp %s", resp)
        bucket_policy = self.get_bucket_policy(self.req.xml(ACL.max_xml_length))
        self.req.bucket_policy = bucket_policy
        self.logger.debug("bucket_policy %s", bucket_policy)



class MultiObjectDeleteAclHandler(BucketPolicyHandler):
    """
    MultiObjectDeleteAclHandler: Handler for MultiObjectDeleteController
    """
    def HEAD(self, app):
        # Only bucket write acl is required
        if not self.obj:
            return self._handle_acl(app, 'HEAD')

    def DELETE(self, app):
        # Only bucket write acl is required
        pass


class MultiUploadAclHandler(BucketPolicyHandler):
    """
    MultiUpload stuff requires acl checking just once for BASE container
    so that MultiUploadAclHandler extends BaseAclHandler to check acl only
    when the verb defined. We should define the verb as the first step to
    request to backend Swift at incoming request.

    Basic Rules:
      - BASE container name is always w/o 'MULTIUPLOAD_SUFFIX'
      - Any check timing is ok but we should check it as soon as possible.

    ========== ====== ============= ==========
    Controller Verb   CheckResource Permission
    ========== ====== ============= ==========
    Part       PUT    Container     WRITE
    Uploads    GET    Container     READ
    Uploads    POST   Container     WRITE
    Upload     GET    Container     READ
    Upload     DELETE Container     WRITE
    Upload     POST   Container     WRITE
    ========== ====== ============= ==========

    """
    def __init__(self, req, logger, **kwargs):
        super(MultiUploadAclHandler, self).__init__(req, logger, **kwargs)
        self.acl_checked = False

    def handle_acl(self, app, method, container=None, obj=None, headers=None):
        method = method or self.method
        ah = self.request_with(container, obj, headers)
        # MultiUpload stuffs don't need acl check basically.
        if hasattr(ah, method):
            return getattr(ah, method)(app)

    def HEAD(self, app):
        # For _check_upload_info
        self._handle_acl(app, 'HEAD', self.container, '')


class PartAclHandler(MultiUploadAclHandler):
    """
    PartAclHandler: Handler for PartController
    """
    def __init__(self, req, logger, **kwargs):
        # pylint: disable-msg=E1003
        super(MultiUploadAclHandler, self).__init__(req, logger, **kwargs)

    def HEAD(self, app):
        if self.container.endswith(MULTIUPLOAD_SUFFIX):
            # For _check_upload_info
            container = self.container[:-len(MULTIUPLOAD_SUFFIX)]
            self._handle_acl(app, 'HEAD', container, '')
        else:
            # For check_copy_source
            return self._handle_acl(app, 'HEAD', self.container, self.obj)


class UploadsAclHandler(MultiUploadAclHandler):
    """
    UploadsAclHandler: Handler for UploadsController
    """
    def handle_acl(self, app, method, *args, **kwargs):
        method = method or self.method
        if hasattr(self, method):
            return getattr(self, method)(app)
        else:
            pass

    def GET(self, app):
        # List Multipart Upload
        self._handle_acl(app, 'GET', self.container, '')

    def PUT(self, app):
        if not self.acl_checked:
            resp = self._handle_acl(app, 'HEAD', obj='')
            req_acl = ACL.from_headers(self.req.headers,
                                       resp.bucket_acl.owner,
                                       Owner(self.user_id, self.user_id))
            acl_headers = encode_acl('object', req_acl)
            self.req.headers[sysmeta_header('object', 'tmpacl')] = \
                acl_headers[sysmeta_header('object', 'acl')]
            self.acl_checked = True


class UploadAclHandler(MultiUploadAclHandler):
    """
    UploadAclHandler: Handler for UploadController
    """
    def handle_acl(self, app, method, *args, **kwargs):
        method = method or self.method
        if hasattr(self, method):
            return getattr(self, method)(app)
        else:
            pass

    def HEAD(self, app):
        # FIXME: GET HEAD case conflicts with GET service
        method = 'GET' if self.method == 'GET' else 'HEAD'
        self._handle_acl(app, method, self.container, '')

    def PUT(self, app):
        container = self.req.container_name + MULTIUPLOAD_SUFFIX
        obj = '%s/%s' % (self.obj, self.req.params['uploadId'])
        resp = self.req._get_response(app, 'HEAD', container, obj)
        self.req.headers[sysmeta_header('object', 'acl')] = \
            resp.sysmeta_headers.get(sysmeta_header('object', 'tmpacl'))


"""
ACL_MAP =
    {
        ('<s3_method>', '<swift_method>', '<swift_resource>'):
        {'Resource': '<check_resource>',
         'Permission': '<check_permission>'},
        ...
    }

s3_method: Method of S3 Request from user to s3api
swift_method: Method of Swift Request from s3api to swift
swift_resource: Resource of Swift Request from s3api to swift
check_resource: <container/object>
check_permission: <OWNER/READ/WRITE/READ_ACP/WRITE_ACP>
"""
ACL_MAP = {
    # HEAD Bucket
    ('HEAD', 'HEAD', 'container'):
    {'Permission': 'READ'},
    # GET Service
    ('GET', 'HEAD', 'container'):
    {'Permission': 'OWNER'},
    # GET Bucket, List Parts, List Multipart Upload
    ('GET', 'GET', 'container'):
    {'Permission': 'READ'},
    # PUT Object, PUT Object Copy
    ('PUT', 'HEAD', 'container'):
    {'Permission': 'WRITE'},
    # DELETE Bucket
    ('DELETE', 'DELETE', 'container'):
    {'Permission': 'OWNER'},
    # HEAD Object
    ('HEAD', 'HEAD', 'object'):
    {'Permission': 'READ'},
    # GET Object
    ('GET', 'GET', 'object'):
    {'Permission': 'READ'},
    # PUT Object Copy, Upload Part Copy
    ('PUT', 'HEAD', 'object'):
    {'Permission': 'READ'},
    # Abort Multipart Upload
    ('DELETE', 'HEAD', 'container'):
    {'Permission': 'WRITE'},
    # Delete Object
    ('DELETE', 'DELETE', 'object'):
    {'Resource': 'container',
     'Permission': 'WRITE'},
    # Complete Multipart Upload, DELETE Multiple Objects,
    # Initiate Multipart Upload
    ('POST', 'HEAD', 'container'):
    {'Permission': 'WRITE'},
    # Versioning
    ('PUT', 'POST', 'container'):
    {'Permission': 'WRITE'},
    ('DELETE', 'GET', 'container'):
    {'Permission': 'WRITE'},
}
