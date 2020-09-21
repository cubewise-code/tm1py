# -*- coding: utf-8 -*-

import collections
import json
from enum import Enum
from typing import Iterable, Optional, List, Dict, Union

from TM1py.Objects.TM1Object import TM1Object
from TM1py.Utils.Utils import CaseAndSpaceInsensitiveSet, format_url


class UserType(Enum):
    User = 0
    SecurityAdmin = 1
    DataAdmin = 2
    Admin = 3
    OperationsAdmin = 4

    def __str__(self):
        return self.name

    @classmethod
    def _missing_(cls, value: str):
        for member in cls:
            if member.name.lower() == value.replace(" ", "").lower():
                return member
        # default
        raise ValueError("Invalid element type=" + value)


class User(TM1Object):
    """ Abstraction of a TM1 User
    
    """

    def __init__(self, name: str, groups: Iterable[str], friendly_name: Optional[str] = None,
                 password: Optional[str] = None, user_type: Union[UserType, str] = None, enabled: bool = None):
        self._name = name
        self._groups = CaseAndSpaceInsensitiveSet(*groups)
        self._friendly_name = friendly_name
        self._password = password
        self._enabled = enabled
        self._user_type = user_type
        # determine user_type
        if user_type is None:
            if str(UserType.Admin) in self._groups:
                self.user_type = UserType.Admin
            elif str(UserType.SecurityAdmin) in self._groups:
                self.user_type = UserType.SecurityAdmin
            elif str(UserType.DataAdmin) in self._groups:
                self.user_type = UserType.DataAdmin
            elif str(UserType.OperationsAdmin) in self._groups:
                self.user_type = UserType.OperationsAdmin
            else:
                self.user_type = UserType.User
        else:
            self.user_type = user_type

    @property
    def name(self) -> str:
        return self._name

    @property
    def user_type(self) -> UserType:
        return self._user_type

    @property
    def friendly_name(self) -> str:
        return self._friendly_name

    @property
    def password(self) -> str:
        if self._password:
            return self._password

    @property
    def is_admin(self) -> bool:
        return 'ADMIN' in self.groups

    @property
    def groups(self) -> List[str]:
        return [group for group in self._groups]

    @property
    def enabled(self) -> bool:
        return self._enabled

    @name.setter
    def name(self, value: str):
        self._name = value

    @friendly_name.setter
    def friendly_name(self, value: str):
        self._friendly_name = value

    @password.setter
    def password(self, value: str):
        self._password = value

    @enabled.setter
    def enabled(self, value: Union[bool, None]):
        self._enabled = value

    @user_type.setter
    def user_type(self, value: Union[str, UserType]):
        if not isinstance(value, str) and not isinstance(value, UserType):
            raise ValueError("argument 'user_type' must be of type str or UserType")

        self._user_type = UserType(value)
        # update groups as well, since TM1 doesn't react to change in user_type property
        if self._user_type is not UserType.User:
            self.add_group(str(self._user_type))

    def add_group(self, group_name: str):
        self._groups.add(group_name)

    def remove_group(self, group_name: str):
        self._groups.discard(group_name)

    @classmethod
    def from_json(cls, user_as_json: str):
        """ Alternative constructor

        :param user_as_json: user as JSON string
        :return: user, an instance of this class
        """
        user_as_dict = json.loads(user_as_json)
        return cls.from_dict(user_as_dict)

    @classmethod
    def from_dict(cls, user_as_dict: Dict) -> 'User':
        """ Alternative constructor

        :param user_as_dict: user as dict
        :return: user, an instance of this class
        """
        return cls(name=user_as_dict['Name'],
                   friendly_name=user_as_dict['FriendlyName'],
                   enabled=user_as_dict["Enabled"],
                   user_type=user_as_dict["Type"],
                   groups=[group["Name"] for group in user_as_dict['Groups']])

    @property
    def body(self) -> str:
        return self.construct_body()

    def construct_body(self) -> str:
        """
        construct body (json) from the class attributes
        :return: String, TM1 JSON representation of a user
        """
        body_as_dict = collections.OrderedDict()
        body_as_dict['Name'] = self.name
        body_as_dict['FriendlyName'] = self.friendly_name or self.name
        body_as_dict['Enabled'] = self._enabled
        body_as_dict['Type'] = str(self._user_type)
        if self.password:
            body_as_dict['Password'] = self._password
        body_as_dict['Groups@odata.bind'] = [format_url("Groups('{}')", group)
                                             for group
                                             in self.groups]
        return json.dumps(body_as_dict, ensure_ascii=False)
