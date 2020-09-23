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

    if tm1.sandboxes.exists("myBox"):
        tm1.sandboxes.delete("myBox")
        print("deleted")
    else:
        box = Sandbox("myBox")
        tm1.sandboxes.create(box)
        print("created")

