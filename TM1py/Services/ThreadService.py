import json

from TM1py.Services.ObjectService import ObjectService


class ThreadService(ObjectService):
    """ Service to Query and Cancel Threads in TM1
    
    """
    def __init__(self, rest):
        super().__init__(rest)

    def get_threads(self):
        """ Return a dict of the currently running threads from the TM1 Server

            :return:
                dict: the response
        """
        request = '/api/v1/Threads'
        response = self._rest.GET(request)
        response_as_dict = json.loads(response)['value']
        return response_as_dict

    def cancel_thread(self, thread_id):
        """ Kill a running thread
        
        :param thread_id: 
        :return: 
        """
        request = "/api/v1/Threads('{}')/tm1.CancelOperation".format(thread_id)
        response = self._rest.POST(request, '')
        return response
