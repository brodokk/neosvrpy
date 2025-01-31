"""
This module define the client who will do the request to the
NeosVR API.
"""

import dataclasses
import json
import logging
from datetime import datetime
from uuid import uuid4
from os import path as OSpath
from typing import Dict, List
from urllib.parse import ParseResult, urlparse

import dacite
from requests import Session
from requests import exceptions as requests_exceptions
from dateutil.parser import isoparse

from . import __version__
from .classes import (
    LoginDetails,
    NeosDirectory,
    NeosFriend,
    NeosLink,
    NeosRecord,
    NeosUser,
    NeosUserStatus,
    NeosMessage,
    NeosMessageType,
    neosMessageTypeMapping,
    NeosCloudVar,
    RecordType,
    recordTypeMapping,
    OnlineStatus,
    CurrentSessionAccessLevel,
    FriendStatus,
    OwnerType,
    NeosCloudVarDefs,
    Session as NeosSession,
)
from .utils import (
    nested_asdict_factory,
    getOwnerType,
)

from .endpoints import CLOUDX_NEOS_API
from neosvrpy import exceptions as neos_exceptions

DACITE_CONFIG = dacite.Config(
    cast=[
        NeosMessageType,
        RecordType,
        OnlineStatus,
        CurrentSessionAccessLevel,
        FriendStatus
    ],
    type_hooks={
        datetime: isoparse,
        ParseResult: urlparse,
    },
)

AUTHFILE_NAME = "auth.token"


@dataclasses.dataclass
class Client:
    """Representation of a neosvrpy NeosVR client."""
    userId: str = None
    token: str = None
    expire: datetime = None  # This don't seems to be use by the API.
    rememberMe: bool = False
    lastUpdate: datetime = None
    secretMachineId: str = None
    session: Session = Session()


    @property
    def headers(self) -> dict:
        default = {"User-Agent": f"neosvrpy/{__version__}"}
        if not self.userId or not self.token:
            logging.warning("WARNING: headers sections not set. this might throw an error soon...")
            return default
        default["Authorization"] = f"neos {self.userId}:{self.token}"
        return default

    @staticmethod
    def processRecordList(data: List[dict]):
        ret = []
        for raw_item in data:
            item = dacite.from_dict(NeosRecord, raw_item, DACITE_CONFIG)
            x = dacite.from_dict(recordTypeMapping[item.recordType], raw_item, DACITE_CONFIG)
            ret.append(x)
        return ret

    def _request(
            self, verb: str, path: str, data: dict = None, json: dict = None,
            params: dict = None, ignoreUpdate: bool = False
        ) -> Dict:
        if self.lastUpdate and not ignoreUpdate:
            lastUpdate = self.lastUpdate
            # From PolyLogix/CloudX.js, the token seems to expire after 3600000 seconds
            if (datetime.now() - lastUpdate).total_seconds() <= 3600000:
                self._request('patch', '/userSessions', ignoreUpdate=True)
                self.lastUpdate = datetime.now()
            # While the API dont seems to implement more security, official client behavior must be respected.
            # Only disconnect after 1 day of inactivity for now.
            # TODO: Implement disconnection after 1 week of inactivity when implementing the rememberMe feature.
            #if 64800 >= (datetime.now() - lastUpdate).total_seconds() >= 85536:
            #    self._request('patch', '/userSessions', ignoreUpdate=True)
            else:
                raise neos_exceptions.InvalidToken("Token expired")
        args = {'url': CLOUDX_NEOS_API + path}
        if data: args['data'] = data
        if json: args['json'] = json
        if params: args['params'] = params
        func = getattr(self.session, verb, None)
        with func(**args) as req:
            logging.debug("NeosAPI: [{}] {}".format(req.status_code, args))
            if req.status_code not in [200, 204]:
                if "Invalid credentials" in req.text:
                    raise neos_exceptions.InvalidCredentials(req.text)
                elif req.status_code == 403:
                    raise neos_exceptions.InvalidToken(req.headers)
                else:
                    raise neos_exceptions.NeosAPIException(req)
            if req.status_code == 200:
                try:
                    response = req.json()
                    if "message" in response:
                        raise neos_exceptions.NeosAPIException(req, message=response["message"])
                    return response
                except requests_exceptions.JSONDecodeError:
                    return req.text
            # In case of a 204 response
            return

    def login(self, data: LoginDetails) -> None:
        response = self._request('post', "/userSessions",
            json=dataclasses.asdict(data))
        self.userId = response["userId"]
        self.token = response["token"]
        self.secretMachineId = response["secretMachineId"]
        self.expire = isoparse(response["expire"])
        self.lastUpdate = datetime.now()
        self.session.headers.update(self.headers)

    def logout(self) -> None:
        self._request('delete',
            "/userSessions/{}/{}".format(self.userId, self.token),
            ignoreUpdate=True,
        )
        self.clean_session()

    def clean_session(self) -> None:
        self.userId = None
        self.token = None
        self.expire = None
        self.secretMachineId = None
        self.lastUpdate = None
        del self.session.headers["Authorization"]
        self.session.headers.update(self.headers)

    def loadToken(self):
        if OSpath.exists(AUTHFILE_NAME):
            with open(AUTHFILE_NAME, "r") as f:
                session = json.load(f)
                expire = datetime.fromisoformat(session["expire"])
                if datetime.now().timestamp() < expire.timestamp():
                    self.token = session["token"]
                    self.userId = session["userId"]
                    self.expire = expire
                    self.secretMachineId = session["secretMachineId"]
                    self.session.headers.update(self.headers)
                else:
                    raise neos_exceptions.NoTokenError
        else:
            raise neos_exceptions.NoTokenError

    def saveToken(self):
        with open(AUTHFILE_NAME, "w+") as f:
            json.dump(
                {
                    "userId": self.userId,
                    "expire": self.expire.isoformat(),
                    "token": self.token,
                    "secretMachineId": self.secretMachineId,
                },
                f,
            )

    def neosDBSignature(self, url: str) -> str:
        return url.split("//")[1].split(".")[0]

    def neosDbToHttp(self, iconUrl: str) -> str:
        url = "https://assets.neos.com/assets"
        url = url + self.neosDBSignature(iconUrl)
        return url

    def getUserData(self, user: str = None) -> NeosUser:
        if user is None:
            user = self.userId
        response = self._request('get', "/users/" + user)
        return dacite.from_dict(NeosUser, response, DACITE_CONFIG)

    def getSession(self, session_id: str) -> NeosSession:
        """ Return session information.
        """
        response = self._request('get', f'/sessions/{session_id}')
        return dacite.from_dict(NeosSession, response, DACITE_CONFIG)

    def getUserStatus(self, user: str = None) -> NeosUser:
        if user is None:
            user = self.userId
        response = self._request('get', '/users/' + user + '/status/')
        return dacite.from_dict(NeosUserStatus, response, DACITE_CONFIG)

    def getFriends(self):
        """
        returns the friends you have.

        Note: does not create friends out of thin air. you need to do that yourself.
        """
        response = self._request('get', f"/users/{self.userId}/friends")
        return [dacite.from_dict(NeosFriend, user, DACITE_CONFIG) for user in response]

    def getInventory(self) -> List[NeosRecord]:
        """
        The typical entrypoint to the inventory system.
        """
        response = self._request(
            'get',
            f"/users/{self.userId}/records",
            params={"path": "Inventory"},
        )
        return self.processRecordList(response)

    def getDirectory(self, directory: NeosDirectory) -> List[NeosRecord]:
        """
        given a directory, return it's contents.
        """
        response = self._request(
            'get',
            f"/users/{directory.ownerId}/records",
            params={"path": directory.content_path},
        )
        return self.processRecordList(response)

    def resolveLink(self, link: NeosLink) -> NeosDirectory:
        """
        given a link type record, will return it's directory. directoy can be passed to getDirectory
        """
        _, user, record = link.assetUri.path.split("/")  # TODO: better
        response = self._request(
            'get',
            f"/users/{user}/records/{record}",
        )
        return dacite.from_dict(NeosDirectory, response, DACITE_CONFIG)

    def buildMessage(
        self, sender_id: str, recipiend_id: str, msg: str
    ) -> NeosMessage:
        message_type = NeosMessageType.TEXT
        builded_msg = {
            'id': f'MSG-{uuid4()}',
            'senderId': sender_id,
            'ownerId': sender_id,
            'sendTime': datetime.now().isoformat(),
            'recipientId': recipiend_id,
            'messageType': message_type,
            'content': msg,
        }
        return dacite.from_dict(NeosMessage, builded_msg, DACITE_CONFIG)

    def sendMessageLegacy(
        self, sender_id: str, recipiend_id: str, msg: str
    ) -> None:
        self._request(
            'post',
            f'/users/{recipiend_id}/messages',
            json=dataclasses.asdict(
                self.buildMessage(sender_id, recipiend_id, msg),
                dict_factory=nested_asdict_factory,
            )
        )

    def getMessageLegacy(
        self, fromTime: str = None, maxItems: int = 100,
        user: str = None, unreadOnly: bool = False
    ) -> None:
        params = {}
        if fromTime:
            raise ValueError('fromTime is not yet implemented')
        params['maxItems'] = maxItems
        params['unreadOnly'] = unreadOnly
        if user:
            params['user'] = user
        return self._request(
            'get',
            f'/users/{self.userId}/messages',
            params=params
        )

    def getOwnerPath(self, ownerId: str) -> str:
        ownerType = getOwnerType(ownerId)
        if ownerType == OwnerType.USER:
            return "users"
        elif ownerType == OwnerType.GROUP:
            return "groups"
        else:
            raise ValueError(f"invalid ownerType for {ownerId}")

    def listCloudVar(self, ownerId: str) -> List[NeosCloudVar]:
        response = self._request(
            'get',
            f'/{self.getOwnerPath(ownerId)}/{ownerId}/vars'
        )
        return [dacite.from_dict(NeosCloudVar, cloud_var, DACITE_CONFIG) for cloud_var in response]

    def getCloudVar(self, ownerId: str, path: str) -> NeosCloudVar:
        response = self._request(
            'get',
            f'/{self.getOwnerPath(ownerId)}/{ownerId}/vars/{path}'
        )
        return dacite.from_dict(NeosCloudVar, response, DACITE_CONFIG)

    def getCloudVarDefs(self, ownerId: str, path: str) -> NeosCloudVarDefs:
        response = self._request(
            'get',
            f'/{self.getOwnerPath(ownerId)}/{ownerId}/vardefs/{path}'
        )
        return dacite.from_dict(NeosCloudVarDefs, response, DACITE_CONFIG)

    def setCloudVar(self, ownerId: str, path: str, value: str) -> None:
        return self._request(
            'put',
            f'/{self.getOwnerPath(ownerId)}/{ownerId}/vars/{path}',
            json = {
                "ownerId": ownerId,
                "path": path,
                "value": value,
            }
        )

    def searchUser(self, username: str) -> dict:
        """ 
        return a list of user based on username.

        This is not the U- NeosVR user id, the API will search over usernames not ids.
        """
        return self._request(
            'get',
            '/users',
            params = {'name': username}
        )
