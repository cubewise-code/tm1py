from TM1py.Services import TM1Service
from TM1py.Objects import Sandbox
from TM1py.Utils import *

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

    box = Sandbox("tst1")

    tm1.sandboxes.create(box)

    tm1.cubes.cells.write_value(
        value=999,
        cube_name="c1",
        element_tuple=["Line_003", "v2"],
        sandbox_name=box.name,
    )

    tm1.sandboxes.publish(box.name)

    # cs = tm1.cubes.cells.execute_mdx(mdx,sandbox_name="box11")
    # df = build_pandas_dataframe_from_cellset(cs)
    # print(df)
    #
    # cs = tm1.cubes.cells.execute_mdx(mdx)
    # df = build_pandas_dataframe_from_cellset(cs)
    # print(df)
