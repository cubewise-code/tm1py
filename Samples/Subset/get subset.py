from Services.RESTService import RESTService
from Services.SubsetService import SubsetService
from Services.LoginService import LoginService


login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    subset_service = SubsetService(tm1_rest)

    private_subsets = subset_service.get_all_names('plan_department', 'plan_department', True)
    print('private subsets: ')
    for subset_name in private_subsets:
        subset = subset_service.get('plan_department', subset_name, True)
        print(subset.name)

    public_subsets = subset_service.get_all_names('plan_department', 'plan_department', False)
    print('public subsets: ')
    for subset_name in public_subsets:
        subset = subset_service.get('plan_department', subset_name, False)
        print(subset.name)
