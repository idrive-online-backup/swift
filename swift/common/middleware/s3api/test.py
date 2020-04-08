def from_list(f, x):
    return [f(y) for y in x]


def from_str(x):
    return x


def to_class(c, x):
    return x.to_dict()



class IPAddress:
    def __init__(self, aws_source_ip):
        self.aws_source_ip = aws_source_ip

    @staticmethod
    def from_dict(obj):
        aws_source_ip = from_str(obj.get(u"aws:SourceIp"))
        return IPAddress(aws_source_ip)

    def to_dict(self):
        result = {}
        result[u"aws:SourceIp"] = from_str(self.aws_source_ip)
        return result


class Condition:
    def __init__(self, ip_address, not_ip_address):
        self.ip_address = ip_address
        self.not_ip_address = not_ip_address

    @staticmethod
    def from_dict(obj):
        ip_address = IPAddress.from_dict(obj.get(u"IpAddress"))
        not_ip_address = IPAddress.from_dict(obj.get(u"NotIpAddress"))
        return Condition(ip_address, not_ip_address)

    def to_dict(self):
        result = {}
        result[u"IpAddress"] = to_class(IPAddress, self.ip_address)
        result[u"NotIpAddress"] = to_class(IPAddress, self.not_ip_address)
        return result


class Principal:
    def __init__(self, aws):
        self.aws = aws

    @staticmethod
    def from_dict(obj):
        if isinstance(obj.get(u"AWS"), list):
            aws = from_list(from_str, obj.get(u"AWS"))
        else:
            aws = from_str(obj.get(u"AWS"))
        return Principal(aws)

    def to_dict(self):
        result = {}
        if isinstance(self.aws, list):
            result[u"AWS"] = from_list(from_str, self.aws)
        else:
            result[u"AWS"] = from_str(self.aws)
        return result


class Statement:
    def __init__(self, sid, effect, principal, action, resource, condition=None):
        self.sid = sid
        self.effect = effect
        self.principal = principal
        self.action = action
        self.resource = resource
        self.condition = condition

    @staticmethod
    def from_dict(obj):
        Statement.validate(obj)
        sid = None
        if obj.get(u"Sid"):
            sid = from_str(obj.get(u"Sid"))
        effect = from_str(obj.get(u"Effect"))
        if isinstance(obj.get(u"Principal"), dict):
            principal = Principal.from_dict(obj.get(u"Principal"))
        else:
            principal = from_str(obj.get(u"Principal"))
        if isinstance(obj.get(u"Action"), list):
            action = from_list(from_str, obj.get(u"Action"))
        else:
            action = from_str(obj.get(u"Action"))
        if isinstance(obj.get(u"Resource"), list):
            resource = from_list(from_str, obj.get(u"Resource"))
        else:
            resource = from_str(obj.get(u"Resource"))
        condition = None
        if obj.get(u"Condition"):
            condition = Condition.from_dict(obj.get(u"Condition"))
        return Statement(sid, effect, principal, action, resource, condition)

    @staticmethod
    def validate(obj):
        if not obj.get(u"Effect") or\
                not obj.get(u"Principal") or\
                not obj.get(u"Action") or\
                not obj.get(u"Resource"):
            raise AttributeError

    def to_dict(self):
        result = {}
        if self.sid:
            result[u"Sid"] = from_str(self.sid)
        result[u"Effect"] = from_str(self.effect)
        if isinstance(self.principal, Principal):
            result[u"Principal"] = to_class(Principal, self.principal)
        else:
            result[u"Principal"] = from_str(self.principal)
        if isinstance(self.action, list):
            result[u"Action"] = from_list(from_str, self.action)
        else:
            result[u"Action"] = from_str(self.action)
        if isinstance(self.resource, list):
            result[u"Resource"] = from_list(from_str, self.resource)
        else:
            result[u"Resource"] = from_str(self.resource)
        if self.condition:
            result[u"Condition"] = to_class(Condition, self.condition)
        return result


class BucketPolicy:
    def __init__(self, id, version, statement):
        self.id = id
        self.version = version
        self.statement = statement

    @staticmethod
    def from_dict(obj):
        try:
            BucketPolicy.validate(obj)
            id = None
            if obj.get(u"Id"):
                id = from_str(obj.get(u"Id"))
            version = None
            if obj.get(u"Version"):
                version = from_str(obj.get(u"Version"))
            statement = from_list(Statement.from_dict, obj.get(u"Statement"))
        except Exception as ex:
            raise AttributeError
        return BucketPolicy(id, version, statement)

    @staticmethod
    def validate(obj):
        if not obj.get(u"Statement"):
            raise AttributeError

    def to_dict(self):
        try:
            result = {}
            if self.id:
                result[u"Id"] = from_str(self.id)
            if self.version:
                result[u"Version"] = self.version
            result[u"Statement"] = from_list(lambda x: to_class(Statement, x), self.statement)
        except Exception as ex:
            raise AttributeError
        return result

if __name__ == '__main__':
    policy_dict = {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"*"},"Action":"s3:GetObject","Resource":"arn:aws:s3:::examplebucket/*"}]}
    print(type(policy_dict))
    bp = BucketPolicy.from_dict(policy_dict)
    print(bp)
    policy_dict_from_dict = bp.to_dict()
    print(policy_dict_from_dict)
    # print(policy_dict == policy_dict_from_dict)

    stmt = Statement(None, "Allow", Principal("*"), "*", "arn:aws:s3:::bp-root/*", None)
    bucket_policy = BucketPolicy(None, "2020-04-06", [stmt])
    import json
    print(json.dumps(bucket_policy.to_dict()))

