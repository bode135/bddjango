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


# ?????????????????????
def get_authorization_header(request):
    auth = request.META.get('HTTP_AUTHORIZATION', b'')
    if isinstance(auth, type('')):
        auth = auth.encode(HTTP_HEADER_ENCODING)
    return auth


# ??????????????????????????????????????????????????????????????????
class ExpiringTokenAuthentication(BaseAuthentication):
    model = Token

    def authenticate(self, request):
        auth = get_authorization_header(request)
        if not auth:
            return None
        try:
            token = auth.decode()
        except UnicodeError:
            msg = ugettext_lazy("?????????Token??? Token???????????????????????????")
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, key):
        # ???????????????????????????????????????????????????????????????????????????????????????????????????????????????
        # token_cache = 'token_' + key
        # cache_user = cache.get(token_cache)
        # if cache_user:
        #     return cache_user, cache_user   # ??????????????????????????????????????????????????????
        # ????????????????????????

        # ??????????????????????????????????????????
        try:
            token = self.model.objects.get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed("????????????")

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed("???????????????")

        # Token???????????????????????????????????????????????????
        # ????????????????????????????????? USE_TZ = False???????????????utc?????????????????????
        # if (datetime.datetime.now() - token.created) > datetime.timedelta(hours=10):
        #     raise exceptions.AuthenticationFailed('?????????????????????')

        # ????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????
        # if token:
        #     token_cache = 'token_' + key
        #     cache.set(token_cache, token.user, 24 * 7 * 60 * 60)

        # ??????????????????
        return token.user, token

    def authenticate_header(self, request):
        return 'Token'


class NoLoginAuthentication(BaseAuthentication):
    """
    ??????????????????????????????
    """
    model = Token

    def process_no_token(self, auth):
        """
        ?????????auth?????????, ?????????????????????, ????????????????????????
        """
        pass

    def authenticate(self, request):
        auth = get_authorization_header(request)
        self.process_no_token(auth)

        try:
            token = auth.decode()
        except UnicodeError:
            msg = "?????????Token??? Token???????????????????????????"
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
                    ????????????token??????
                    """
                    user = AnonymousUser()  # ????????????
            else:
                token = tokens[0]
                if not token.user.is_active:
                    msg = "???????????????"
                    raise MyValidationError(detail={
                        'status': status.HTTP_403_FORBIDDEN,
                        'msg': msg
                    })
            return token.user, token
        except self.model.DoesNotExist:
            msg = "????????????"
            raise MyValidationError(detail={
                'status': status.HTTP_401_UNAUTHORIZED,
                'msg': msg
            })

    def authenticate_header(self, request):
        return 'Token'


class MustLoginAuthentication(NoLoginAuthentication):
    """
    ???????????????????????????
    """
    def process_no_token(self, auth):
        """
        ?????????auth?????????
        """
        if not auth:
            raise MyValidationError(detail={
                'status': status.HTTP_401_UNAUTHORIZED,
                'msg': "????????????!"
            })


from functools import wraps


def my_permission_decorator(status_code=status.HTTP_403_FORBIDDEN, msg="FORBIDDEN"):
    """
    permission?????????

    - ??????ret???False, ???????????????MyValidationError
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



