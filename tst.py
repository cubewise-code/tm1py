from TM1py.Services import TM1Service

with TM1Service(
    address="localhost",
    port=8010,
    user="admin",
    password="",
    ssl=True,
    async_requests_mode=True,
) as tm1:

    box = tm1.sandboxes.get("box2")
    print(box.name)

    # print(cube)
    # print(tm1.sandboxes.get("box21111"))
