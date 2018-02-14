# -*- coding: utf-8 -*-

from TM1py.Objects import Application


class ApplicationService:
    """ Service to Read and Write TM1 Applications

    """

    def __init__(self, tm1_rest):
        """

        :param tm1_rest: 
        """
        self._rest = tm1_rest

    def get(self, path):
        """ Get Excel Application from TM1 Server in binary format. Can be dumped to file.
        
        :param path: path through folder structur to application. For instance: "Finance/P&L.xlsx"
        :return: Return application as binary. Can be dumped to file:
            with open("out.xlsx", "wb") as out:
                out.write(content)
        """
        mid = "".join(['/Contents(\'{}\')'.format(element) for element in path.split('/')])
        request = "/api/v1/Contents('Applications')" + mid[:-2] + ".blob')/Document/Content"
        response = self._rest.GET(request)
        content = response.content

        return Application(path, content)



