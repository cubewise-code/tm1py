import uuid

from Services.RESTService import RESTService
from Services.LoginService import LoginService
from Services.ViewService import ViewService
from Services.DataService import DataService

from Objects.MDXView import MDXView

login = LoginService.native('admin', 'apple')

with RESTService(ip='', port=8001, login=login, ssl=False) as tm1_rest:
    # Setup services
    view_service = ViewService(tm1_rest)
    data_service = DataService(tm1_rest)
    # Random text
    random_string = str(uuid.uuid4())

    # Create mdx view
    mdx = "SELECT " \
          "NON EMPTY {TM1SUBSETALL( [}Clients] )} on ROWS, " \
          "NON EMPTY {TM1SUBSETALL( [}Groups] )} ON COLUMNS " \
          "FROM [}ClientGroups]"
    mdx_view = MDXView(cube_name='}ClientGroups', view_name='TM1py_' + random_string, MDX=mdx)

    # Create mdx view on TM1 Server
    view_service.create(view=mdx_view)

    # Get view content
    content = data_service.get_view_content(cube_name=mdx_view.cube, view_name=mdx_view.name)

    # Print content
    print(content)



