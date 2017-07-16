import uuid

from Services.RESTService import RESTService
from Services.SubsetService import SubsetService
from Services.LoginService import LoginService
from Objects.Subset import Subset

login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    subset_service = SubsetService(tm1_rest)

    subset_name = str(uuid.uuid4())


    # create subset
    s = Subset(dimension_name='Plan_Department', subset_name=subset_name, alias='', elements=['200', '405', '410'])
    subset_service.create(s, True)

    # get it and print out the elements
    s = subset_service.get(dimension_name='Plan_Department', subset_name=subset_name, private=True)
    print(s.elements)

    # delete it
    subset_service.delete(dimension_name='Plan_Department', subset_name=subset_name, private=True)

