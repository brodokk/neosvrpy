from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import PureWindowsPath
from typing import List, Optional

from neosvrpy.secrets import generate
from neosvrpy.exceptions import NeosException

from urllib.parse import ParseResult


class RecordType(Enum):
    OBJECT = "object"
    LINK = "link"
    DIRECTORY = "directory"
    WORLD = "world"
    TEXTURE = "texture"
    AUDIO = "audio"


@dataclass
class NeosRecord:
    id: str
    globalVersion: int
    localVersion: int
    lastModifyingUserId: Optional[str]
    name: str
    recordType: RecordType
    path: Optional[str]
    isPublic: bool
    isForPatrons: bool
    isListed: bool
    isDeleted: bool
    lastModificationTime: datetime
    visits: int
    rating: int
    ownerId: str


@dataclass
class NeosLink(NeosRecord):
    assetUri: ParseResult


@dataclass
class NeosDirectory(NeosRecord):
    lastModifyingMachineId: Optional[str]
    ownerName: str
    tags: List[str]
    creationTime: Optional[datetime]

    @property
    def content_path(self) -> str:
        return str(PureWindowsPath(self.path, self.name))


@dataclass
class NeosObject(NeosRecord):
    assetUri: str
    lastModifyingMachineId: str
    ownerName: str
    tags: List[str]
    creationTime: datetime

@dataclass
class NeosWorld(NeosRecord):
    pass

@dataclass
class NeosTexture(NeosRecord):
    pass

@dataclass
class NeosAudio(NeosRecord):
    pass


recordTypeMapping = {
    RecordType.DIRECTORY: NeosDirectory,
    RecordType.LINK: NeosLink,
    RecordType.OBJECT: NeosObject,
    RecordType.WORLD: NeosWorld,
    RecordType.TEXTURE: NeosTexture,
    RecordType.AUDIO: NeosAudio,
}


@dataclass
class LoginDetails:
    """
    the login details for neos. SecretMachineId can be generated by neos.secrets
    """

    ownerId: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    secretMachineId: str = field(default_factory=generate)
    rememberMe: Optional[str] = False

    def __post_init__(self):
        if not self.ownerId and not self.username and not self.email:
            raise NeosException(
                'Either an ownerId, an username or an email is needed')
        if not self.password:
            raise NeosException('A password is needed')


@dataclass
class ProfileData:
    iconUrl: Optional[str]
    tokenOutOut: Optional[List[str]]


@dataclass
class CreditData:
    KFC: float
    NCR: float
    CDFT: float


@dataclass
class PatreonData:
    isPatreonSupporter: bool
    patreonId: Optional[str]
    lastPatreonPledgeCents: int
    lastTotalCents: int
    minimumTotalUnits: int
    externalCents: int
    lastExternalCents: int
    hasSupported: bool
    lastIsAnorak: bool
    priorityIssue: int
    lastPlusActivationTime: datetime
    lastActivationTime: datetime
    lastPlusPledgeAmount: int
    lastPaidPledgeAmount: int
    accountName: str
    currentAccountType: int
    currentAccountCents: int
    pledgedAccountType: int


@dataclass
class NeosUser:
    id: str
    username: str
    normalizedUsername: str
    email: Optional[str]
    registrationDate: datetime
    isVerified: bool
    quotaBytes: Optional[int]
    isLocked: bool
    accountBanExpiration: Optional[datetime]
    publicBanExpiration: Optional[datetime]
    spectatorBanExpiration: Optional[datetime]
    muteBanExpiration: Optional[datetime]
    usedBytes: Optional[int]
    profile: Optional[ProfileData]
    credits: Optional[CreditData]
    NCRdepositAddress: Optional[str]
    patreonData: Optional[PatreonData]
    tags: Optional[List[str]] = field(default_factory=list)

@dataclass
class WorldId:
    ownerId: str
    recordId: str

@dataclass
class SessionUser:
    isPresent: bool
    userID: Optional[str]
    username: str

@dataclass
class Session:
    activeSessions: Optional[str]
    activeUsers: int
    compatibilityHash: Optional[str]
    correspondingWorldId: Optional[WorldId]
    description: Optional[str]
    hasEnded: bool
    headlessHost: bool
    hostMachineId: str
    hostUserId: str
    hostUsername: str
    isValid: bool
    joinedUsers: int
    lastUpdate: datetime
    maxUsers: int
    mobileFriendly: bool
    name: str
    neosVersion: str
    normalizedSessionId: str
    sessionBeginTime: datetime
    sessionId: str
    sessionURLs: List[str]
    sessionUsers: List[SessionUser]
    tags: List[str]
    thumbnail: Optional[str]
    totalActiveUsers: int
    totalJoinedUsers: int


@dataclass
class PublicRSAKey:
    Exponent: str
    Modulus: str


class OnlineStatus(Enum):
    ONLINE = "Online"
    AWAY = "Away"
    BUSY = "Busy"
    OFFLINE = "Offline"


onlineStatusMapping = {
    OnlineStatus.ONLINE: "Online",
    OnlineStatus.AWAY: "Away",
    OnlineStatus.BUSY: "Busy",
    OnlineStatus.OFFLINE: "Offline",
}


class CurrentSessionAccessLevel(Enum):
    PRIVATE = 0
    LAN = 1
    FRIENDS = 2
    FRIENDSOFFRIENDS = 3
    REGISTEREDUSERS = 4
    ANYONE = 5

    def __str__(self):
        text = {
            'PRIVATE': 'Private',
            'LAN': 'LAN',
            'FRIENDS': 'Contacts',
            'FRIENDSOFFRIENDS': 'Contacts+',
            'REGISTEREDUSERS': 'Registered Users',
            'ANYONE': 'Anyone'
        }
        return text[self.name]


currentSessionAccessLevelMapping = {
    CurrentSessionAccessLevel.PRIVATE: 0,
    CurrentSessionAccessLevel.LAN: 1,
    CurrentSessionAccessLevel.FRIENDS: 2,
    CurrentSessionAccessLevel.FRIENDSOFFRIENDS: 3,
    CurrentSessionAccessLevel.REGISTEREDUSERS: 4,
    CurrentSessionAccessLevel.ANYONE: 5,
}


@dataclass
class UserStatusData:
    activeSessions: Optional[List[Session]]
    currentSession: Optional[Session]
    compatibilityHash: Optional[str]
    currentHosting: bool
    currentSessionAccessLevel: CurrentSessionAccessLevel
    currentSessionHidden: bool
    currentSessionId: Optional[str]
    isMobile: bool
    lastStatusChange: datetime
    neosVersion: Optional[str]
    onlineStatus: OnlineStatus
    OutputDevice: Optional[str]
    publicRSAKey: Optional[PublicRSAKey]


class FriendStatus(Enum):
    ACCEPTED = "Accepted"
    IGNORED = "Ignored"
    REQUESTED = "Requested"
    NONE = "None"


friendStatusMapping = {
    FriendStatus.ACCEPTED: "Accepted",
    FriendStatus.IGNORED: "Ignored",
    FriendStatus.REQUESTED: "Requested",
    FriendStatus.NONE: "None",
}


@dataclass
class NeosFriend:
    id: str
    friendUsername: str
    friendStatus: FriendStatus
    isAccepted: bool
    userStatus: UserStatusData
    profile: Optional[ProfileData]
    latestMessageTime: datetime

class NeosMessageType(Enum):
    TEXT = "Text"
    OBJECT = "Object"
    SOUND = "Sound"
    SESSIONINVITE = "SessionInvite"
    CREDITTRANSFER = "CreditTransfer"
    SUGARCUBES = "SugarCubes"

neosMessageTypeMapping = {
    NeosMessageType.TEXT: "Text",
    NeosMessageType.OBJECT: "Object",
    NeosMessageType.SOUND: "Sound",
    NeosMessageType.SESSIONINVITE: "SessionInvite",
    NeosMessageType.CREDITTRANSFER: "CreditTransfer",
    NeosMessageType.SUGARCUBES: "SugarCubes",
}

@dataclass
class NeosMessage:
    id: str
    senderId: str
    ownerId: str
    sendTime: str
    recipientId: str
    messageType: NeosMessageType
    content: str

@dataclass
class NeosCloudVar:
    ownerId: str
    path: str
    value: str
    partitionKey: str
    rowKey: str
    timestamp: str
    eTag: str