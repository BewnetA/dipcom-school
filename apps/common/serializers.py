from __future__ import annotations

from copy import deepcopy


def serialize_meta(meta: dict) -> dict:
	return deepcopy(meta)


def serialize_flags(flags: dict) -> dict:
	return deepcopy(flags)
