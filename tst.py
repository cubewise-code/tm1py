from TM1py.Services import TM1Service
from TM1py.Objects import Sandbox

with TM1Service(
    address="localhost",
    port=8010,
    user="admin",
    password="",
    ssl=True,
    async_requests_mode=True,
) as tm1:
    """
    select 
    {[Measure].[s1]} on 0,
    {[Line].[s1]} on 1
    from [c1]
    """
    mdx = "select \
    {[Measure].[s1]} on 0,\
    {[Line].[s1]} on 1\
    from [c1]"
    tm1.sandboxes.set_sandbox("box2")
    z = tm1.cubes.cells.clear_spread(
        cube="c1", unique_element_names=["[Line].[Line_005]", "[Measure].[v1]"]
    )

    tm1.sandboxes.set_base()
    z = tm1.cubes.cells.clear_spread(
        cube="c1", unique_element_names=["[Line].[Line_005]", "[Measure].[v1]"]
    )
    # z = tm1.cubes.cells.execute_mdx(mdx)
    print(z)
