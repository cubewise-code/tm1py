import json
from typing import Dict, List

from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import format_url
from TM1py.Utils.Utils import CaseAndSpaceInsensitiveDict, require_ops_admin


class LoggerService(ObjectService):
    """ Service to query and update loggers

    """

    def __init__(self, rest: RestService):
        super().__init__(rest)

    @require_ops_admin
    def get_all(self, **kwargs) -> Dict:
        url = f"/Loggers"
        loggers = self._rest.GET(url, **kwargs).json()
        return loggers['value']

    @require_ops_admin
    def get_all_names(self, **kwargs) -> List[str]:
        loggers = self.get_all(**kwargs)
        return [logger['Name'] for logger in loggers]

    @require_ops_admin
    def get(self, logger: str, **kwargs) -> Dict:
        """ Get level for specified logger

        :param logger: string name of logger
        :return: Dict of logger and level
        """
        url = format_url("/Loggers('{}')", logger)
        logger = self._rest.GET(url, **kwargs).json()
        del logger["@odata.context"]
        return logger

    @require_ops_admin
    def search(self, wildcard: str = '', level: str = '', **kwargs) -> Dict:
        """ Searches logger names by wildcard or by level. Combining wildcard and level will filter via AND and not OR

        :param wildcard: string to match in logger name
        :param level: string e.g. FATAL, ERROR, WARNING, INFO, DEBUG, UNKOWN, OFF
        :return: Dict of matching loggers and levels
        """
        url = f"/Loggers"

        logger_filters = []

        if level:
            level_dict = CaseAndSpaceInsensitiveDict(
                {'FATAL': 0, 'ERROR': 1, 'WARNING': 2, 'INFO': 3, 'DEBUG': 4, 'UNKNOWN': 5, 'OFF': 6}
            )
            level_index = level_dict.get(level)
            if level_index:
                logger_filters.append("Level eq {}".format(level_index))

        if wildcard:
            logger_filters.append("contains(tolower(Name), tolower('{}'))".format(wildcard))

        url += "?$filter={}".format(" and ".join(logger_filters))

        loggers = self._rest.GET(url, **kwargs).json()
        return loggers['value']

    @require_ops_admin
    def exists(self, logger: str, **kwargs) -> bool:
        """ Test if logger exists
        :param logger: string name of logger
        :return: bool
        """
        url = format_url("/Loggers('{}')", logger)
        return self._exists(url, **kwargs)

    @require_ops_admin
    def set_level(self, logger: str, level: str, **kwargs):
        """ Set logger level
        :param logger: string name of logger
        :param level: string e.g. FATAL, ERROR, WARNING, INFO, DEBUG, UNKOWN, OFF
        :return: response
        """
        url = format_url("/Loggers('{}')", logger)

        if not self.exists(logger=logger, **kwargs):
            raise ValueError('{} is not a valid logger'.format(logger))

        level_dict = CaseAndSpaceInsensitiveDict(
            {'FATAL': 0, 'ERROR': 1, 'WARNING': 2, 'INFO': 3, 'DEBUG': 4, 'UNKNOWN': 5, 'OFF': 6}
        )
        level_index = level_dict.get(level)
        if level_index:
            logger = {'Level': level_index}
        else:
            raise ValueError('{} is not a valid level'.format(level))

        return self._rest.PATCH(url, json.dumps(logger))
