import uuid
from TM1py import Subset, TM1Queries

random_string1 = str(uuid.uuid4())
random_string2 = str(uuid.uuid4())

q = TM1Queries(ip='', port=8008, user='admin', password='apple', ssl=True)

# create dynamic subset
s = Subset(dimension_name='plan_business_unit', subset_name=random_string1,
           expression='{ HIERARCHIZE( {TM1SUBSETALL( [plan_business_unit] )} ) }')
response = q.create_subset(s)

# create static subset
s = Subset(dimension_name='plan_business_unit', subset_name=random_string2,
           elements=['10000', '10000', '10000', '10000', '10000', '10000', '10000', '10000', '10000'])
response = q.create_subset(s)

# delete subset
q.delete_subset(name_dimension='plan_business_unit', name_subset=random_string1)
q.delete_subset(name_dimension='plan_business_unit', name_subset=random_string2)

# logout
q.logout()
