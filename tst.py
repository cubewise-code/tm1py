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

    z = tm1.sandboxes.merge("box2", "box11")
    tm1.sandboxes.publish("box11")

    print(z)

