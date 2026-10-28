"""API client for the SMART tag parent portal."""

from __future__ import annotations

import asyncio
import socket
from urllib.parse import unquote

import aiohttp
from yarl import URL

from .data import LiveActivity, Ride, Student

API_ORIGIN = URL("https://api-parentapp-prod.azurewebsites.net/")


class SmartTagApiError(Exception):
    """Exception to indicate a general API error."""


class SmartTagApiNetworkError(SmartTagApiError):
    """Exception to indicate a network error."""


class SmartTagApiAuthError(SmartTagApiError):
    """Exception to indicate an authentication error."""


def _raise_response_error(response: aiohttp.ClientResponse) -> None:
    """Raise an error based on the response code."""
    if response.status in (401, 403):
        raise SmartTagApiAuthError("invalid or expired credentials")
    # handle 400/404 manually
    if response.status not in (400, 404):
        response.raise_for_status()


class SmartTagApiClient:
    """API client for the new SMART tag backend."""

    access_token = None
    refresh_token = None

    def __init__(
        self,
        session: aiohttp.ClientSession,
        access_token: str | None = None,
        refresh_token: str | None = None,
        api_origin: URL = API_ORIGIN,
    ) -> None:
        """Initialize the API client"""
        self._api_origin = api_origin
        self.refresh_token = refresh_token
        self.access_token = access_token
        self._session = session

    async def login(self, email: str, password: str):
        """Login to the API and get a token"""
        self.refresh_token = None
        self.access_token = None

        response = await self._api_wrapper(
            "POST", "user/login", {"username": email, "password": password}
        )
        if response.status == 400:
            # invalid auth credentials
            raise SmartTagApiAuthError("invalid email or password")
        json = await response.json()

        # refresh token in cookie
        refresh_token = response.cookies.get("refreshToken")
        if refresh_token:
            self.refresh_token = unquote(refresh_token.value)

        self.access_token = json["token"]

    async def refresh_access_token(self):
        """Refresh the access token"""
        if self.access_token is None or self.refresh_token is None:
            raise SmartTagApiAuthError("not authenticated")

        data = {"token": self.access_token, "refreshToken": self.refresh_token}
        response = await self._api_wrapper("POST", "user/refresh", data=data)

        if not response.ok:
            raise SmartTagApiAuthError("need reauthentication")

        json = await response.json()

        # refresh token in cookie
        refresh_token = response.cookies.get("refreshToken")
        if refresh_token:
            self.refresh_token = unquote(refresh_token.value)

        self.access_token = json["token"]

    async def get_students(self):
        """Get a list of the user's students."""
        if self.access_token is None:
            raise SmartTagApiAuthError("not authenticated")

        response = await self._authed_api_wrapper("GET", "parent/all-students")

        return [Student.from_dict(d) for d in await response.json()]

    async def get_rides(self, student_id: str | int, limit: int):
        """Get the {limit} most recent rides for this student"""
        if self.access_token is None:
            raise SmartTagApiAuthError("not authenticated")

        query = {"studentid": student_id, "pageIndex": 0, "pageSize": limit}
        response = await self._authed_api_wrapper(
            "GET", "student/riding-activity", query=query
        )
        json = await response.json()

        rides = (Ride.from_dict(d) for d in json["data"])
        return [ride for ride in rides if ride is not None]

    async def get_live_activity(self, student_id: str | int) -> LiveActivity | None:
        """Get the live bus position for this student (None if unavailable)."""
        if self.access_token is None:
            raise SmartTagApiAuthError("not authenticated")

        response = await self._authed_api_wrapper(
            "GET", "student/live-activity", query={"studentId": student_id}
        )
        if not response.ok:
            return None
        try:
            json = await response.json()
        except (aiohttp.ContentTypeError, ValueError):
            return None
        return LiveActivity.from_dict(json)

    async def get_photo(self, photo_location: str) -> tuple[bytes, str] | None:
        """Get a student's photo as (bytes, content type); None if there is none."""
        if self.access_token is None:
            raise SmartTagApiAuthError("not authenticated")

        # photoLocation is a relative API path, e.g. "student/photo?studentId=1"
        path, _, query = photo_location.partition("?")
        params = dict(pair.split("=", 1) for pair in query.split("&") if "=" in pair)
        response = await self._authed_api_wrapper("GET", path, query=params)
        content_type = response.headers.get("Content-Type", "").split(";")[0]
        if not response.ok or not content_type.startswith("image/"):
            return None
        return await response.read(), content_type

    async def _api_wrapper(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        query: dict | None = None,
        headers: dict | None = None,
    ):
        """Make a call to the SMART Tag API with error handling."""
        url = self._api_origin / path
        if query:
            url = url.with_query(query)
        try:
            async with asyncio.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                )
                _raise_response_error(response)
                return response

        except SmartTagApiError:
            raise
        except TimeoutError as exception:
            err = f"Timeout error fetching information - {exception}"
            raise SmartTagApiNetworkError(err) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            err = f"Error fetching information - {exception}"
            raise SmartTagApiNetworkError(err) from exception
        except Exception as exception:  # pylint: disable=broad-except
            err = f"Something really wrong happened! - {exception}"
            raise SmartTagApiError(err) from exception

    async def _authed_api_wrapper(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        query: dict | None = None,
    ):
        """Make an authenticated call to the SMART Tag API with error handling"""
        # add bearer token
        headers = (
            {"Authorization": f"Bearer {self.access_token}"}
            if self.access_token is not None
            else None
        )

        try:
            return await self._api_wrapper(method, path, data, query, headers)
        except SmartTagApiAuthError:
            # try to reauthenticate
            await self.refresh_access_token()

            # new bearer token
            headers = (
                {"Authorization": f"Bearer {self.access_token}"}
                if self.access_token is not None
                else None
            )

            return await self._api_wrapper(method, path, data, query, headers)
