from TM1py.Services import DataService
from TM1py.Services import LoginService
from TM1py.Services import RESTService
from TM1py.Services import UserService

login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    # Setup Services
    user_service = UserService(tm1_rest)
    data_service = DataService(tm1_rest)

    # Get all groups
    all_groups = user_service.get_all_groups()

    # Determine the used groups from }ClientGroups Cube
    mdx = "SELECT NON EMPTY {TM1SUBSETALL( [}Clients] )} on ROWS, NON EMPTY {TM1SUBSETALL( [}Groups] )} ON COLUMNS " \
          "FROM [}ClientGroups]"
    cube_content = data_service.execute_mdx(mdx, ['Value'])

    used_groups = {cell['Value'] for cell in cube_content.values() if cell['Value'] != ''}

    # Determine the unused groups
    unused_groups = set(all_groups) - used_groups

    # Print out the unused groups
    print(unused_groups)
