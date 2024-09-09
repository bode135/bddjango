from bddjango import APIView, APIResponse, my_api_assert_function, get_list, Time
from . import models
from bddjango import CompleteModelView
from bddjango import BaseListView


class Test(APIView):
    def get(self, request, *args, **kwargs):
        ret = 'hello, world!'
        return APIResponse(ret, msg='ok', status=200)

