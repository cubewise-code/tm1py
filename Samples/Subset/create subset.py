import uuid
from TM1py import Subset, TM1pyQueries as TM1, TM1pyLogin

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    subset_name = str(uuid.uuid4())

    # create subset
    s = Subset(dimension_name='Plan_Department', subset_name=subset_name, alias='', elements=['200', '405', '410'])
    tm1.create_subset(s, True)

    # get it and print out the elements
    s = tm1.get_subset(dimension_name='Plan_Department', subset_name=subset_name, private=True)
    print(s.elements)

    # delete it
    tm1.delete_subset(dimension_name='Plan_Department', subset_name=subset_name , private=True)

