from django.utils.encoding import force_str
from rest_framework.utils.serializer_helpers import ReturnList, ReturnDict
from rest_framework.exceptions import APIException, ErrorDetail, status
from django.utils.translation import ugettext_lazy
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from rest_framework.authtoken.models import Token
from rest_framework import HTTP_HEADER_ENCODING
from django.contrib.auth.models import AnonymousUser


def _get_error_details(data, default_code=None):
    """
    Descend into a nested data structure, forcing any
    lazy translation strings or strings into `ErrorDetail`.
    """
    if isinstance(data, list):
        ret = [
            _get_error_details(item, default_code) for item in data
        ]
        if isinstance(data, ReturnList):
            return ReturnList(ret, serializer=data.serializer)
        return ret
    elif isinstance(data, dict):
        ret = {
            key: _get_error_details(value, default_code)
            for key, value in data.items()
        }
        if isinstance(data, ReturnDict):
            return ReturnDict(ret, serializer=data.serializer)
        return ret

    text = force_str(data)
    code = getattr(data, 'code', default_code)
    return ErrorDetail(text, code)


class MyApiError(APIException):
    status_code = status.HTTP_200_OK
    default_detail = ('Invalid input.', )
    default_code = 'invalid'

    def __init__(self, detail=None, code=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code

        # For validation failures, we may collect many errors together,
        # so the details should always be coerced to a list if not already.
        if not isinstance(detail, dict) and not isinstance(detail, list):
            detail = [detail]

        self.detail = _get_error_details(detail, code)


class MyValidationError(APIException):
    status_code = status.HTTP_200_OK
    default_detail = ('Invalid input.')
    default_code = 'invalid'

    def __init__(self, detail=None, code=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code

        # For validation failures, we may collect many errors together,
        # so the details should always be coerced to a list if not already.
        if not isinstance(detail, dict) and not isinstance(detail, list):
            detail = [detail]

        self.detail = _get_error_details(detail, code)


def get_my_api_error(status=status.HTTP_404_NOT_FOUND, msg="Error!"):
    ret = MyApiError(detail={
                'status': status,
                'msg': msg,
                'result': [],
            })

    return ret


def my_api_assert_function(assert_sentence, msg='error', status=404):
    if not assert_sentence:
        raise get_my_api_error(status=status, msg=msg)
    return 1


# 获取请求头信息
def get_authorization_header(request):
    auth = request.META.get('HTTP_AUTHORIZATION', b'')
    if isinstance(auth, type('')):
        auth = auth.encode(HTTP_HEADER_ENCODING)
    return auth


# 自定义认证方式，这个是后面要添加到设置文件的
class ExpiringTokenAuthentication(BaseAuthentication):
    model = Token

    def authenticate(self, request):
        auth = get_authorization_header(request)
        if not auth:
            return None
        try:
            token = auth.decode()
        except UnicodeError:
            msg = ugettext_lazy("无效的Token， Token头不应包含无效字符")
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, key):
        # 尝试从缓存获取用户信息（设置中配置了缓存的可以添加，不加也不影响正常功能）
        # token_cache = 'token_' + key
        # cache_user = cache.get(token_cache)
        # if cache_user:
        #     return cache_user, cache_user   # 这里需要返回一个列表或元组，原因不详
        # 缓存获取到此为止

        # 下面开始获取请求信息进行验证
        try:
            token = self.model.objects.get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed("认证失败")

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed("用户被禁用")

        # Token有效期时间判断（注意时间时区问题）
        # 我在设置里面设置了时区 USE_TZ = False，如果使用utc这里需要改变。
        # if (datetime.datetime.now() - token.created) > datetime.timedelta(hours=10):
        #     raise exceptions.AuthenticationFailed('认证信息已过期')

        # 加入缓存增加查询速度，下面和上面是配套的，上面没有从缓存中读取，这里就不用保存到缓存中了
        # if token:
        #     token_cache = 'token_' + key
        #     cache.set(token_cache, token.user, 24 * 7 * 60 * 60)

        # 返回用户信息
        return token.user, token

    def authenticate_header(self, request):
        return 'Token'


class NoLoginAuthentication(BaseAuthentication):
    """
    不需要要登录也能使用
    """
    model = Token

    def process_no_token(self, auth):
        """
        处理没auth的情况, 此处不需要登录, 所以不做其它处理
        """
        pass

    def authenticate(self, request):
        auth = get_authorization_header(request)
        self.process_no_token(auth)

        try:
            token = auth.decode()
        except UnicodeError:
            msg = "无效的Token， Token头不应包含无效字符"
            raise MyValidationError(detail={
                'status': status.HTTP_417_EXPECTATION_FAILED,
                'msg': msg
            })
        return self.authenticate_credentials(token)

    def authenticate_credentials(self, key):
        try:
            tokens = self.model.objects.filter(key=key)
            if tokens.count() == 0:
                class token:
                    """
                    伪造一个token回去
                    """
                    user = AnonymousUser()  # 匿名用户
            else:
                token = tokens[0]
                if not token.user.is_active:
                    msg = "用户被禁用"
                    raise MyValidationError(detail={
                        'status': status.HTTP_403_FORBIDDEN,
                        'msg': msg
                    })
            return token.user, token
        except self.model.DoesNotExist:
            msg = "认证失败"
            raise MyValidationError(detail={
                'status': status.HTTP_401_UNAUTHORIZED,
                'msg': msg
            })

    def authenticate_header(self, request):
        return 'Token'


class MustLoginAuthentication(NoLoginAuthentication):
    """
    必须要登录才能使用
    """
    def process_no_token(self, auth):
        """
        处理没auth的情况
        """
        if not auth:
            raise MyValidationError(detail={
                'status': status.HTTP_401_UNAUTHORIZED,
                'msg': "请先登录!"
            })


from functools import wraps


def my_permission_decorator(status_code=status.HTTP_403_FORBIDDEN, msg="FORBIDDEN"):
    """
    permission装饰器

    - 如果ret为False, 则抛出一个MyValidationError
    """
    def permission_decorator(func):
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            ret = func(*args, **kwargs)
            if bool(ret):
                return True
            else:
                e = get_my_validation_error(status=status_code, msg=msg)
                raise e
        return wrapped_function
    return permission_decorator



