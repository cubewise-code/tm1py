from TM1py import TM1pyQueries as TM1, TM1pyLogin

login = TM1pyLogin.native('admin', 'apple')

with TM1(ip='', port=8001, login=login, ssl=False) as tm1:
    # get all groups
    all_groups = tm1.get_all_groups()

    # determine the used groups from }ClientGroups Cube
    mdx = "SELECT NON EMPTY {TM1SUBSETALL( [}Clients] )} on ROWS, NON EMPTY {TM1SUBSETALL( [}Groups] )} ON COLUMNS " \
          "FROM [}ClientGroups]"
    cube_content = tm1.execute_mdx(mdx, '}ClientGroups', ['Value'])
    used_groups = {cell['Value'] for cell in cube_content.values() if cell['Value'] != ''}

    # determine the unused groups
    unused_groups = set(all_groups) - used_groups

    # print out the unused groups
    print(unused_groups)
