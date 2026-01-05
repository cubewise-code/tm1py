import responses

from .SmokeTestBase import SmokeTestBase


class TestDimensionSmoke(SmokeTestBase):

    def test_dimension_metadata(self):

        self.rsps.add(
            responses.GET,
            f"{self.base_url}/Dimensions",
            json={
                "@odata.context": "$metadata#Dimensions",
                "value": [
                    {
                        "@odata.etag": 'W/"0a8190dd72c21841bda16b3fd8492f171df98aa7"',
                        "Name": "}Clients",
                        "UniqueName": "[}Clients]",
                        "AllLeavesHierarchyName": "",
                        "Attributes": {"Caption": "}Clients"},
                    },
                    {
                        "@odata.etag": 'W/"e4bd6cb79066cc3936a5af517dece606b3f5f3d5"',
                        "Name": "}Groups",
                        "UniqueName": "[}Groups]",
                        "AllLeavesHierarchyName": "",
                        "Attributes": {"Caption": "}Groups"},
                    },
                ],
            },
            status=200,
        )

        names = self.tm1.dimensions.get_all_names()

        self.assertIn("}Clients", names)
        self.assertIn("}Groups", names)
