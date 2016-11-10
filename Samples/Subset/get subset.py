import uuid
from TM1py import Subset, TM1pyQueries as TM1, TM1pyLogin

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    private_subsets = tm1.get_all_subset_names('plan_department', 'plan_department', True)
    print('private subsets: ')
    for subset_name in private_subsets:
        subset = tm1.get_subset('plan_department', subset_name, True)
        print(subset.name)
    public_subsets = tm1.get_all_subset_names('plan_department', 'plan_department', False)
    
    print('public subsets: ')
    for subset_name in public_subsets:
        subset = tm1.get_subset('plan_department', subset_name, False)
        print(subset.name)
