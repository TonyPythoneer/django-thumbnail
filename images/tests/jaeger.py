"""Jaeger HTTP API client + typed response schemas. Test-only."""

import json
import time
import urllib.request
from typing import NotRequired, TypedDict

from django.conf import settings

JaegerValue = str | int | float | bool

_POLL_MAX = 2
_POLL_INTERVAL = 3
_REQUEST_TIMEOUT = 5


class KeyedValue(TypedDict):
    key: str
    type: str
    value: JaegerValue


class Process(TypedDict):
    serviceName: str
    tags: list[KeyedValue]


class SpanLog(TypedDict):
    timestamp: int
    fields: list[KeyedValue]


class SpanReference(TypedDict):
    refType: str
    traceID: str
    spanID: str


class Span(TypedDict):
    traceID: str
    spanID: str
    operationName: str
    references: list[SpanReference]
    startTime: int
    duration: int
    tags: list[KeyedValue]
    logs: list[SpanLog]
    processID: str
    warnings: NotRequired[list[str] | None]


class TraceData(TypedDict):
    traceID: str
    spans: list[Span]
    processes: dict[str, Process]
    warnings: NotRequired[list[str] | None]


class JaegerResponse(TypedDict):
    data: list[TraceData]
    total: int
    limit: int
    offset: int
    errors: list[object] | None


_EMPTY_RESPONSE: JaegerResponse = JaegerResponse(data=[], total=0, limit=0, offset=0, errors=None)


class JaegerClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def fetch_trace(self, trace_id: str) -> JaegerResponse:
        url = f"{self._base_url}/api/traces/{trace_id}"
        with urllib.request.urlopen(url, timeout=_REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read())

    def poll_trace(self, trace_id: str) -> JaegerResponse:
        data = _EMPTY_RESPONSE
        for _ in range(_POLL_MAX):
            data = self.fetch_trace(trace_id)
            if data.get("errors") is None and data.get("data"):
                return data
            time.sleep(_POLL_INTERVAL)
        return data

    @staticmethod
    def extract_events(data: JaegerResponse, operation_name: str | None = None) -> list[str]:
        """Pull `event` field values from Jaeger logs across spans in the trace.

        operation_name=None scans every span (useful when the span name is
        owned by an auto-instrumentor whose naming may shift between releases).
        """
        events: list[str] = []
        for trace_obj in data.get("data", []):
            for span in trace_obj.get("spans", []):
                if operation_name is not None and span.get("operationName") != operation_name:
                    continue
                for log in span.get("logs", []):
                    for field in log.get("fields", []):
                        if field.get("key") == "event":
                            events.append(str(field.get("value")))
        return events

    @staticmethod
    def services_in_trace(data: JaegerResponse) -> set[str]:
        if not data.get("data"):
            return set()
        return {p["serviceName"] for p in data["data"][0]["processes"].values()}


jaeger_client = JaegerClient(base_url=settings.SMOKE_JAEGER_BASE_URL)
