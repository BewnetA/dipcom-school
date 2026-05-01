from __future__ import annotations

from django.http import JsonResponse
from django.views import View

from .services import get_common_health, get_common_meta, get_feature_flags


class CommonMetaView(View):
	def get(self, _request):
		return JsonResponse(get_common_meta())


class CommonFlagsView(View):
	def get(self, _request):
		return JsonResponse(get_feature_flags())


def common_health(_request):
	return JsonResponse(get_common_health())
