# -*- coding: utf-8 -*-
from TM1py.Objects import ElementAttribute, Element
from TM1py.Services.ObjectService import ObjectService
from TM1py.Utils import build_element_unique_names
import json


class ElementService(ObjectService):
    """ Service to handle Object Updates for TM1 Dimension (resp. Hierarchy) Elements
    
    """

    def __init__(self, rest):
        super().__init__(rest)

    def get(self, dimension_name, hierarchy_name, element_name):
        request = "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements('{}')?$expand=*" \
            .format(dimension_name, hierarchy_name, element_name)
        response = self._rest.GET(request)
        return Element.from_dict(response.json())

    def create(self, dimension_name, hierarchy_name, element):
        request = "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements".format(
            dimension_name,
            hierarchy_name)
        return self._rest.POST(request, element.body)

    def update(self, dimension_name, hierarchy_name, element):
        request = "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements('{}')".format(
            dimension_name,
            hierarchy_name,
            element.name)
        return self._rest.PATCH(request, element.body)

    def exists(self, dimension_name, hierarchy_name, element_name):
        request = "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements('{}')".format(
            dimension_name,
            hierarchy_name,
            element_name)
        return self._exists(request)

    def delete(self, dimension_name, hierarchy_name, element_name):
        request = "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements('{}')".format(
            dimension_name,
            hierarchy_name,
            element_name)
        return self._rest.DELETE(request)

    def get_elements(self, dimension_name, hierarchy_name):
        request = "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements?$expand=*" \
            .format(dimension_name, hierarchy_name)
        response = self._rest.GET(request)
        return [Element.from_dict(element) for element in response.json()["value"]]

    def get_leaf_elements(self, dimension_name, hierarchy_name):
        request = "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements?$expand=*&$filter=Type ne 3" \
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
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/Elements?$select=Name'.format(
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(request, '')
        return (e["Name"] for e in response.json()['value'])

    def get_number_of_elements(self, dimension_name, hierarchy_name):
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/Elements?&$count&$top=0'.format(
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(request, '')
        return int(response.json()["@odata.count"])

    def get_number_of_consolidated_elements(self, dimension_name, hierarchy_name):
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/Elements?$filter=Type eq 3&$count&$top=0'.format(
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(request, '')
        return int(response.json()["@odata.count"])

    def get_number_of_leaf_elements(self, dimension_name, hierarchy_name):
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/Elements?$filter=Type ne 3&$count&$top=0'.format(
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(request, '')
        return int(response.json()["@odata.count"])

    def get_all_leaf_element_identifiers(self, dimension_name, hierarchy_name):
        """ Get all element names and alias values for leaf elements in a hierarchy

        :param dimension_name:
        :param hierarchy_name:
        :return:
        """
        mdx_elements = "{{ Tm1FilterByLevel ( {{ Tm1SubsetAll ([{dim}].[{hier}]) }} , 0 ) }}".format(
            dim=dimension_name,
            hier=hierarchy_name)
        return self.get_element_identifiers(dimension_name, hierarchy_name, mdx_elements)

    def get_all_element_identifiers(self, dimension_name, hierarchy_name):
        """ Get all element names and alias values in a hierarchy

        :param dimension_name:
        :param hierarchy_name:
        :return:
        """

        mdx_elements = "{{ Tm1SubsetAll ([{dim}].[{hier}]) }}".format(
            dim=dimension_name,
            hier=hierarchy_name)
        return self.get_element_identifiers(dimension_name, hierarchy_name, mdx_elements)

    def get_element_identifiers(self, dimension_name, hierarchy_name, elements):
        """ Get all element names and alias values for a set of elements in a hierarchy

        :param dimension_name:
        :param hierarchy_name:
        :param elements: MDX (Set) expression or iterable of elements
        :return:
        """
        alias_attributes = self.get_alias_element_attributes(dimension_name, hierarchy_name)

        if isinstance(elements, str):
            mdx_element_selection = elements
        else:
            mdx_element_selection = ",".join(build_element_unique_names(
                [dimension_name] * len(elements),
                elements,
                [hierarchy_name] * len(elements)))
        mdx = """
         SELECT
         {{ {elem_mdx} }} ON ROWS, 
         {{ {attr_mdx} }} ON COLUMNS
         FROM [}}ElementAttributes_{dim}]
         """.format(
            elem_mdx=mdx_element_selection,
            attr_mdx=",".join(build_element_unique_names(
                ["}ElementAttributes_" + dimension_name] * len(alias_attributes),
                alias_attributes)),
            dim=dimension_name)
        return self._retrieve_mdx_rows_and_cell_values_as_string_set(mdx)

    def _retrieve_mdx_rows_and_cell_values_as_string_set(self, mdx):
        from TM1py import CellService
        return CellService(self._rest).execute_mdx_rows_and_values_string_set(mdx)

    def get_alias_element_attributes(self, dimension_name, hierarchy_name):
        """

        :param dimension_name:
        :param hierarchy_name:
        :return:
        """
        attributes = self.get_element_attributes(dimension_name, hierarchy_name)
        return [attr.name
                for attr
                in attributes if attr.attribute_type == 'Alias']

    def get_element_attributes(self, dimension_name, hierarchy_name):
        """ Get element attributes from hierarchy
    
        :param dimension_name:
        :param hierarchy_name:
        :return:
        """
        request = '/api/v1/Dimensions(\'{}\')/Hierarchies(\'{}\')/ElementAttributes'.format(
            dimension_name,
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
        response = self._rest.GET(request, odata_escape_single_quotes_in_object_names=False)
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

    def execute_set_mdx(self, mdx,
                        top_records=None,
                        member_properties = ['Name', 'Weight'],
                        parent_properties = ['Name', 'UniqueName'],
                        element_properties = ['Type', 'Level']):
        '''
        :param mdx: valid dimension mdx statement
        :param top: number of records to return, default: all elements no limit
        :return: dictionary of members, unique names, weights, types, and parents
        '''
        top = f"$top={top_records};" if top_records else ""

        if not member_properties:
            member_properties = ['Name']

        member_properties = ",".join(member_properties)
        select_member_properties = f'$select={member_properties}'

        properties_to_expand = []
        if parent_properties:
            parent_properties = ",".join(parent_properties)
            select_parent_properties = f'$select={parent_properties}'
            expand_parent_properties = f'Parent({select_parent_properties})'
            properties_to_expand.append(expand_parent_properties)

        if element_properties:
            element_properties = ",".join(element_properties)
            select_element_properties = f'$select={element_properties}'
            expand_element_properties = f'Element({select_element_properties})'
            properties_to_expand.append(expand_element_properties)

        if properties_to_expand:
            expand_properties = f';$expand={",".join(properties_to_expand)}'
        else:
            expand_properties = ""


        request = f'/api/v1/ExecuteMDXSetExpression?$expand=Tuples({top}' \
                  f'$expand=Members({select_member_properties}'\
                  f'{expand_properties}))'

        payload = {"MDX": mdx}
        response = self._rest.POST(request, json.dumps(payload, ensure_ascii=False))
        raw_dict = response.json()
        return [tuples['Members'] for tuples in raw_dict['Tuples']]

