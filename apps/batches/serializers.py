from __future__ import annotations

from copy import deepcopy


def serialize_batch(batch: dict) -> dict:
	return deepcopy(batch)


def serialize_batches(batches: list[dict]) -> list[dict]:
	return [serialize_batch(batch) for batch in batches]
