# -*- coding: utf-8 -*-

from base64 import b64encode


class LoginService:
    """ Handle Login for different TM1 login types. Instance of this class to be passed to TM1pyHTTPClient, TM1pyQueries

        :Notes: WIA not implemented.

    """
    def __init__(self, user, password, auth_type, token=None):
        """ Function is called from static methods

        :param user: String - name user
        :param password: string - pwd
        :param auth_type: string - basic, CAM or WIA
        :param token:
        """
        self._user = user
        self._password = password
        self._auth_type = auth_type
        self._token = token

    @property
    def auth_type(self):
        return self._auth_type

    @property
    def token(self):
        return self._token

    @classmethod
    def native(cls, user, password):
        """ Alternate constructor for native login

        :param user:
        :param password:
        :return: instance of TM1pyLogin
        """
        token = 'Basic ' + b64encode(str.encode("{}:{}".format(user, password))).decode("ascii")
        login = cls(user, password, 'native', token)
        return login

    @classmethod
    def CAM(cls, user, password, CAM_namespace):
        """ Alternate constructor for CAM login

        :param user:
        :param password:
        :param CAM_namespace:
        :return: instance of TM1pyLogin
        """
        token = 'CAMNamespace ' + \
                b64encode(str.encode("{}:{}:{}".format(user, password, CAM_namespace))).decode("ascii")
        login = cls(user, password, 'CAM', token)
        return login

    @classmethod
    def WIA_login(cls):
        """ To be implemented :)

        :return: instance of TM1pyLogin
        """
        raise NotImplementedError('not supported')