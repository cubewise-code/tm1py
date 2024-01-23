from warnings import warn

try:
    import pandas as pd
    _has_pandas = True
except ImportError:
    _has_pandas = False

from TM1py.Exceptions import TM1pyVersionException
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils.Utils import format_url, require_pandas, verify_version


class JobService(ObjectService):
    """ Service to handle TM1 Job objects introduced in v12

    """

    def __init__(self, rest: RestService):
        super().__init__(rest)

    @verify_version(version="12.0.0")
    def get(self, **kwargs):
        """ Return a dict of the currently running jobs from the TM1 Server

            :return:
                dict: the response
        """
        url = '/Jobs'
        response = self._rest.GET(url, **kwargs)
        return response.json()['value']

    @verify_version(version="12.0.0")
    def cancel(self, job_id, **kwargs):
        """ Cancels a running Job

        :param job_id:
        :return:
        """
        url = format_url("/Jobs('{}')/tm1.Cancel", str(job_id))
        response = self._rest.POST(url, **kwargs)
        return response

    @verify_version(version="12.0.0")
    def cancel_all(self, **kwargs):
        jobs = self.get()
        canceled_jobs = list()
        for job in jobs:
            self.cancel(job["ID"])
            canceled_jobs.append(job)
        return canceled_jobs

    @require_pandas
    @verify_version(version="12.0.0")
    def get_as_dataframe(self):
        """ Gets jobs and returns them as a dataframe

        """
        jobs = self.get()
        df = pd.DataFrame.from_records(jobs)
        return df


