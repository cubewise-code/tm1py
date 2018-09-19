# -*- coding: utf-8 -*-


from TM1py.Objects import ElementAttribute, Element
from TM1py.Services.ObjectService import ObjectService


class ElementService(ObjectService):
    """ Service to handle Object Updates for TM1 Dimension (resp. Hierarchy) Elements
    
    """
    def __init__(self, rest):
        super().__init__(rest)

    def get(self, dimension_name, hierarchy_name, element_name):
        request = "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements('{}')?$expand=*"\
            .format(dimension_name, hierarchy_name, element_name)
        response = self._rest.GET(request)
        return Element.from_dict(response.json())

    def create(self, dimension_name, hierarchy_name, element):
        request = "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements".format(dimension_name, hierarchy_name)
        return self._rest.POST(request, element.body)

    def update(self, dimension_name, hierarchy_name, element):
        request = "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements('{}')".format(dimension_name, hierarchy_name,
                                                                                     element.name)
        return self._rest.PATCH(request, element.body)

    def exists(self, dimension_name, hierarchy_name, element_name):
        request = "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements('{}')".format(dimension_name, hierarchy_name,
                                                                                     element_name)
        return self._exists(request)

    def delete(self, dimension_name, hierarchy_name, element_name):
        request = "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements('{}')".format(dimension_name, hierarchy_name,
                                                                                     element_name)
        return self._rest.DELETE(request)

    def get_elements(self, dimension_name, hierarchy_name):
        request = "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements?$expand=*"\
            .format(dimension_name, hierarchy_name)
        response = self._rest.GET(request)
        return [Element.from_dict(element) for element in response.json()["value"]]

    def get_leaf_elements(self, dimension_name, hierarchy_name):
        request = "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements?$expand=*&$filter=Type ne 3"\
            .format(dimension_name, hierarchy_name)
        response = self._rest.GET(request)
        return [Element.from_dict(element) for element in response.json()["value"]]

    def get_leaf_element_names(self, dimension_name, hierarchy_name):
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/Elements?$select=Name&$filter=Type ne 3'.format(
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(request, '')
        return (e["Name"] for e in response.json()['value'])

    def get_element_names(self, dimension_name, hierarchy_name):
        """ Get all elementnames
        
        :param dimension_name: 
        :param hierarchy_name: 
        :return: Generator of element-names
        """
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/Elements?$select=Name'.format(dimension_name,
                                                                                                hierarchy_name)
        response = self._rest.GET(request, '')
        return (e["Name"] for e in response.json()['value'])

    def get_element_attributes(self, dimension_name, hierarchy_name):
        """ Get element attributes from hierarchy
    
        :param dimension_name:
        :param hierarchy_name:
        :return:
        """
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/ElementAttributes'.format(dimension_name,
                                                                                            hierarchy_name)
        response = self._rest.GET(request, '')
        element_attributes = [ElementAttribute.from_dict(ea) for ea in response.json()['value']]
        return element_attributes

    def get_elements_filtered_by_attribute(self, dimension_name, hierarchy_name, attribute_name, attribute_value):
        """ Get all elements from a hierarchy with given attribute value
    
        :param dimension_name:
        :param hierarchy_name:
        :param attribute_name:
        :param attribute_value:
        :return: List of element names
        """
        attribute_name = attribute_name.replace(" ", "")
        if isinstance(attribute_value, str):
            request = "/api/v1/Dimensions('{}')/Hierarchies('{}')" \
                      "?$expand=Elements($filter = Attributes/{} eq '{}';$select=Name)" \
                .format(dimension_name, hierarchy_name, attribute_name, attribute_value)
        else:
            request = "/api/v1/Dimensions('{}')/Hierarchies('{}')" \
                      "?$expand=Elements($filter = Attributes/{} eq {};$select=Name)" \
                .format(dimension_name, hierarchy_name, attribute_name, attribute_value)
        response = self._rest.GET(request)
        return [elem['Name'] for elem in response.json()['Elements']]

    def create_element_attribute(self, dimension_name, hierarchy_name, element_attribute):
        """ like AttrInsert

        :param dimension_name:
        :param hierarchy_name:
        :param element_attribute: instance of TM1py.ElementAttribute
        :return:
        """
        request = "/api/v1/Dimensions('{}')/Hierarchies('{}')/ElementAttributes" \
            .format(dimension_name, hierarchy_name)
        return self._rest.POST(request, element_attribute.body)

    def delete_element_attribute(self, dimension_name, hierarchy_name, element_attribute):
        """ like AttrDelete

        :param dimension_name:
        :param hierarchy_name:
        :param element_attribute: instance of TM1py.ElementAttribute
        :return:
        """
        request = "/api/v1/Dimensions('}}ElementAttributes_{}')/Hierarchies('}}ElementAttributes_{}')/Elements('{}')" \
            .format(dimension_name, hierarchy_name, element_attribute)
        return self._rest.DELETE(request, '')

    def get_leaves_under_consolidation(self, dimension_name, hierarchy_name, consolidation, max_depth=None):
        """ Get all leaves under a consolidated element
        
        :param dimension_name: name of dimension
        :param hierarchy_name: name of hierarchy
        :param consolidation: name of consolidated Element
        :param max_depth: 99 if not passed
        :return: 
        """
        return self.get_members_under_consolidation(dimension_name, hierarchy_name, consolidation, max_depth, True)

    def get_members_under_consolidation(self, dimension_name, hierarchy_name, consolidation, max_depth=None,
                                        leaves_only=False):
        """ Get all members under a consolidated element

        :param dimension_name: name of dimension
        :param hierarchy_name: name of hierarchy
        :param consolidation: name of consolidated Element
        :param max_depth: 99 if not passed
        :param leaves_only: Only Leaf Elements or all Elements
        :return:
        """
        depth = max_depth if max_depth else 99
        # members to return
        members = []
        # Build request
        bare_request = "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements('{}')?$select=Name,Type&$expand=Components("
        request = bare_request.format(dimension_name, hierarchy_name, consolidation)
        for _ in range(depth):
            request += "$select=Name,Type;$expand=Components("
        request = request[:-1] + ")" * depth
        response = self._rest.GET(request)
        consolidation_tree = response.json()

        # recursive function to parse consolidation_tree
        def get_members(element):
            if element["Type"] == "Numeric":
                members.append(element["Name"])
            elif element["Type"] == "Consolidated":
                if "Components" in element:
                    for component in element["Components"]:
                        if not leaves_only:
                            members.append(component["Name"])
                        get_members(component)
        get_members(consolidation_tree)
        return members
