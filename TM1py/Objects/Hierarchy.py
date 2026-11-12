# -*- coding: utf-8 -*-

import collections
import json
import warnings
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union

from TM1py.Objects.Element import Element
from TM1py.Objects.ElementAttribute import ElementAttribute
from TM1py.Objects.TM1Object import TM1Object
from TM1py.Utils.Utils import (
    CaseAndSpaceInsensitiveDict,
    CaseAndSpaceInsensitiveTuplesDict,
    case_and_space_insensitive_equals,
    lower_and_drop_spaces,
)


class Hierarchy(TM1Object):
    """Abstraction of TM1 Hierarchy
    Requires reference to a Dimension

    Elements modeled as a Dictionary where key is the element name and value an instance of TM1py.Element
    {
        'US': instance of TM1py.Element,
        'CN': instance of TM1py.Element,
        'AU': instance of TM1py.Element
    }

    ElementAttributes of type TM1py.Objects.ElementAttribute

    Edges are represented as a TM1py.Utils.CaseAndSpaceInsensitiveTupleDict:
    {
        (parent1, component1) : 10,
        (parent1, component2) : 30
    }

    Subsets is list of type TM1py.Subset

    """

    def __init__(
        self,
        name: str,
        dimension_name: str,
        elements: Optional[Iterable["Element"]] = None,
        element_attributes: Optional[Iterable["ElementAttribute"]] = None,
        edges: Optional["Dict"] = None,
        subsets: Optional[Iterable[str]] = None,
        structure: Optional[int] = None,
        default_member: Optional[str] = None,
    ):

        self._name = name
        self._dimension_name = None
        self.dimension_name = dimension_name
        self._elements: Dict[str, Element] = CaseAndSpaceInsensitiveDict()
        if elements:
            for elem in elements:
                self._elements[elem.name] = elem
        self._element_attributes = list(element_attributes) if element_attributes else []
        self._edges = CaseAndSpaceInsensitiveTuplesDict(edges) if edges else CaseAndSpaceInsensitiveTuplesDict()
        self._subsets = list(subsets) if subsets else []
        # balanced is true, false or None (in versions < TM1 11)
        self._balanced = False if not structure else structure == 0
        self._default_member = default_member

    @classmethod
    def from_dict(cls, hierarchy_as_dict: Dict, dimension_name: str = None) -> "Hierarchy":
        # Build the Dictionary for the edges
        edges = CaseAndSpaceInsensitiveTuplesDict(
            {(edge["ParentName"], edge["ComponentName"]): edge["Weight"] for edge in hierarchy_as_dict["Edges"]}
        )

        if not dimension_name:
            dimension_name = hierarchy_as_dict["UniqueName"][1 : hierarchy_as_dict["UniqueName"].find("].[")]

        return cls(
            name=hierarchy_as_dict["Name"],
            dimension_name=dimension_name,
            elements=[Element.from_dict(elem) for elem in hierarchy_as_dict["Elements"]],
            element_attributes=[
                ElementAttribute(ea["Name"], ea["Type"]) for ea in hierarchy_as_dict.get("ElementAttributes", [])
            ],
            edges=edges,
            subsets=[subset["Name"] for subset in hierarchy_as_dict.get("Subsets", [])],
            structure=hierarchy_as_dict["Structure"] if "Structure" in hierarchy_as_dict else None,
            default_member=(
                hierarchy_as_dict["DefaultMember"]["Name"] if hierarchy_as_dict.get("DefaultMember", None) else None
            ),
        )

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def dimension_name(self) -> str:
        return self._dimension_name

    @dimension_name.setter
    def dimension_name(self, dimension_name: str):
        self._dimension_name = dimension_name

    @property
    def elements(self) -> Dict[str, Element]:
        return self._elements

    @property
    def element_attributes(self) -> List[ElementAttribute]:
        return self._element_attributes

    @property
    def edges(self) -> Dict[Tuple[str], Element]:
        return self._edges

    @property
    def subsets(self) -> List[str]:
        return self._subsets

    @property
    def balanced(self) -> bool:
        return self._balanced

    @property
    def default_member(self) -> str:
        return self._default_member

    @property
    def body(self) -> str:
        return json.dumps(self._construct_body())

    @property
    def body_as_dict(self) -> Dict:
        return self._construct_body()

    def contains_element(self, element_name: str) -> bool:
        return element_name in self._elements

    def get_element(self, element_name: str) -> Element:
        if element_name in self._elements:
            return self._elements[element_name]
        else:
            raise ValueError("Element: {} not found in Hierarchy: {}".format(element_name, self.name))

    def get_ancestors(self, element_name: str, recursive: bool = False) -> Set[Element]:
        ancestors = set()

        for parent, component in self._edges:
            if not case_and_space_insensitive_equals(component, element_name):
                continue

            ancestor: Element = self.elements[parent]
            ancestors.add(ancestor)

            if recursive:
                ancestors = ancestors.union(self.get_ancestors(ancestor.name, True))
        return ancestors

    def get_descendants(self, element_name: str, recursive: bool = False, leaves_only=False) -> Set[Element]:
        descendants = set()

        for parent, component in self._edges:
            if not case_and_space_insensitive_equals(parent, element_name):
                continue

            descendant: Element = self.elements[component]
            if not leaves_only:
                descendants.add(descendant)
            else:
                if descendant.element_type == Element.Types.NUMERIC:
                    descendants.add(descendant)

            if recursive and descendant.element_type == Element.Types.CONSOLIDATED:
                descendants = descendants.union(self.get_descendants(descendant.name, True, leaves_only=leaves_only))
        return descendants

    def get_descendant_edges(self, element_name: str, recursive: bool = False) -> Dict:
        descendant_edges = dict()

        for (parent, component), weight in self._edges.items():
            if not case_and_space_insensitive_equals(parent, element_name):
                continue

            descendant_edges[parent, component] = weight
            descendant: Element = self.elements[component]

            if recursive and descendant.element_type == Element.Types.CONSOLIDATED:
                descendant_edges.update(self.get_descendant_edges(descendant.name, True))

        return descendant_edges

    def get_ancestor_edges(self, element_name: str, recursive: bool = False) -> Dict:
        ancestor_edges = dict()

        for (parent, component), weight in self._edges.items():
            if not case_and_space_insensitive_equals(component, element_name):
                continue

            ancestor_edges[parent, component] = weight
            ancestor: Element = self.elements[component]

            if recursive:
                ancestor_edges.update(self.get_ancestor_edges(ancestor.name, True))

        return ancestor_edges

    def add_element(self, element_name: str, element_type: Union[str, Element.Types]):
        if element_name in self._elements:
            raise ValueError("Element name must be unique")

        self._elements[element_name] = Element(name=element_name, element_type=element_type)

    def add_component(self, parent_name: str, component_name: str, weight: int):
        if parent_name not in self._elements:
            raise ValueError(f"Parent '{parent_name}' does not exist in hierarchy")
        if self._elements[parent_name].element_type != Element.Types.CONSOLIDATED:
            raise ValueError(f"Parent '{parent_name}' is not of type 'Consolidated'")

        if component_name not in self.elements:
            self.add_element(component_name, "Numeric")
        elif self._elements[component_name].element_type == Element.Types.STRING:
            raise ValueError(f"Component '{component_name}' must not be of type 'String'")

        self.add_edge(parent_name, component_name, weight)

    def update_element(self, element_name: str, element_type: Union[str, Element.Types]):
        self._elements[element_name].element_type = element_type

    def remove_element(self, element_name: str):
        if element_name not in self._elements:
            return
        del self._elements[element_name]
        self.remove_edges_related_to_element(element_name=element_name)

    def remove_all_elements(self):
        self._elements = CaseAndSpaceInsensitiveDict()
        self.remove_all_edges()

    def add_edge(self, parent: str, component: str, weight: float):
        self._edges[(parent, component)] = weight

    def update_edge(self, parent: str, component: str, weight: float):
        self._edges[(parent, component)] = weight

    def remove_edge(self, parent: str, component: str):
        if (parent, component) in self.edges:
            del self.edges[(parent, component)]

    def remove_edges(self, edges: Iterable[Tuple[str, str]]):
        for edge in edges:
            self.remove_edge(*edge)

    def remove_all_edges(self):
        self._edges = CaseAndSpaceInsensitiveTuplesDict()

    def remove_edges_related_to_element(self, element_name: str):
        element_name_adjusted = lower_and_drop_spaces(element_name)
        edges_to_remove = set()
        for edge in self._edges.adjusted_keys():
            if element_name_adjusted in edge:
                edges_to_remove.add(edge)
        self.remove_edges(edges=edges_to_remove)

    def add_element_attribute(self, name: str, attribute_type: str):
        attribute = ElementAttribute(name, attribute_type)
        if attribute not in self.element_attributes:
            self.element_attributes.append(attribute)

    def remove_element_attribute(self, name: str):
        self._element_attributes = [
            element_attribute
            for element_attribute in self.element_attributes
            if not case_and_space_insensitive_equals(element_attribute.name, name)
        ]

    def replace_element(self, old_element_name: str, new_element_name: str):
        """
        Substitute one element in the hierarchy structure,
        so that all edges are moved from the old element to the new element.
        """
        if old_element_name not in self.elements:
            raise ValueError(f"Element '{old_element_name}' does not exist in hierarchy")

        if new_element_name in self.elements:
            raise ValueError(f"Element '{new_element_name}' already exists in hierarchy")

        element = self.get_element(old_element_name)
        ancestor_edges = self.get_ancestor_edges(old_element_name, recursive=False)
        descendant_edges = self.get_descendant_edges(element_name=old_element_name, recursive=False)

        self.remove_element(element_name=old_element_name)

        self.add_element(element_name=new_element_name, element_type=element.element_type)

        for (ancestor, _), weight in ancestor_edges.items():
            self.add_edge(parent=ancestor, component=new_element_name, weight=weight)
        for (_, descendant), weight in descendant_edges.items():
            self.add_edge(parent=new_element_name, component=descendant, weight=weight)

    def rebase(self, leaf_level: int) -> List[str]:
        """Cut the hierarchy at a TM1 level so that the elements on that level become the new leaves.

        Levels are TM1 levels, counted from the bottom: leaves are level 0 and a consolidation is one level
        above its deepest child. Rebasing a hierarchy whose top is level 8 to ``leaf_level=3`` turns the
        level 3 elements into numeric leaves, removes everything below them and leaves the top at level 5.

        Element names are kept, so the value of a new leaf can be read 1:1 from the (consolidated) cell of
        the same element in the original hierarchy, e.g. to load SKU-level actuals into a product-family plan.
        Loaded like that, every consolidation that remains in the hierarchy adds up to the same total as in
        the original hierarchy, because no remaining consolidation loses a child:

        - Elements on ``leaf_level`` become leaves and everything that is only underneath them is removed.
        - Elements below ``leaf_level`` that sit directly under a consolidation above ``leaf_level``
          (e.g. a short branch in a ragged hierarchy) or that have no parent are kept as leaves too.

        A warning is issued when new leaves share descendants in the original hierarchy (e.g. an alternate
        rollup next to the main rollup). Their values overlap, just as they do in the original hierarchy.

        String elements are not part of the consolidation structure and are left untouched.

        The hierarchy is modified in place.

        :param leaf_level: the TM1 level whose elements become the new leaves. 0 leaves the structure as is.
        :return: names of the new leaves
        """
        if isinstance(leaf_level, bool) or not isinstance(leaf_level, int) or leaf_level < 0:
            raise ValueError(f"'leaf_level' must be a non-negative integer, but received: '{leaf_level}'")

        key = lower_and_drop_spaces
        names = {key(element.name): element.name for element in self._elements.values()}
        children = collections.defaultdict(list)
        parents = collections.defaultdict(list)
        for parent, component in self._edges:
            children[key(parent)].append(key(component))
            parents[key(component)].append(key(parent))

        levels = self._compute_levels(names, children)
        max_level = max(levels.values(), default=0)
        if leaf_level > max_level:
            raise ValueError(
                f"'leaf_level' {leaf_level} exceeds the highest level ({max_level}) "
                f"in hierarchy '{self.dimension_name}:{self.name}'"
            )

        strings = {node for node, name in names.items() if self._elements[name].element_type == Element.Types.STRING}

        # consolidations above leaf_level keep all their children. Everything else at or below leaf_level
        # survives only as a root
        survivors = {
            node
            for node, level in levels.items()
            if level >= leaf_level or not parents[node] or any(levels[p] > leaf_level for p in parents[node])
        }
        new_leaves = {node for node in survivors if levels[node] <= leaf_level and node not in strings}

        overlapping_leaves = self._find_overlapping_leaves(new_leaves, children)
        if overlapping_leaves:
            sample = ", ".join(names[node] for node in overlapping_leaves[:10])
            if len(overlapping_leaves) > 10:
                sample += f" ... (+{len(overlapping_leaves) - 10} more)"
            warnings.warn(
                f"Rebasing hierarchy '{self.dimension_name}:{self.name}' to level {leaf_level}: "
                f"{len(overlapping_leaves)} new leaves share descendants with other new leaves "
                f"(e.g. alternate rollups), so their values overlap as in the original hierarchy: {sample}",
                UserWarning,
                stacklevel=2,
            )

        self._elements = CaseAndSpaceInsensitiveDict(
            {element.name: element for element in self._elements.values() if key(element.name) in survivors}
        )
        self._edges = CaseAndSpaceInsensitiveTuplesDict(
            {
                (parent, component): weight
                for (parent, component), weight in self._edges.items()
                if levels[key(parent)] > leaf_level
            }
        )
        for node in new_leaves:
            self._elements[names[node]].element_type = Element.Types.NUMERIC
        if self._default_member and self._default_member not in self._elements:
            self._default_member = None

        return [element.name for element in self._elements.values() if key(element.name) in new_leaves]

    @staticmethod
    def _compute_levels(names: Dict[str, str], children: Dict[str, List[str]]) -> Dict[str, int]:
        """TM1 level per (adjusted) element name: 0 for leaves, 1 + deepest child level for consolidations"""
        levels = {}
        in_progress = set()
        for start in names:
            stack = [(start, False)]
            while stack:
                node, expanded = stack.pop()
                if expanded:
                    levels[node] = 1 + max((levels[child] for child in children.get(node, ())), default=-1)
                    in_progress.discard(node)
                    continue
                if node in levels:
                    continue
                if node in in_progress:
                    raise ValueError(f"Circular reference in hierarchy involving element '{names.get(node, node)}'")
                in_progress.add(node)
                stack.append((node, True))
                stack.extend((child, False) for child in children.get(node, ()) if child not in levels)
        return levels

    @staticmethod
    def _find_overlapping_leaves(leaves: Set[str], children: Dict[str, List[str]]) -> List[str]:
        """leaves whose descendants are also descendants of another leaf"""
        owner = {leaf: leaf for leaf in leaves}
        overlapping = set()
        for leaf in leaves:
            visited = set()
            stack = list(children.get(leaf, ()))
            while stack:
                node = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                if node in owner and owner[node] != leaf:
                    overlapping.update((leaf, owner[node]))
                owner.setdefault(node, leaf)
                stack.extend(children.get(node, ()))
        return sorted(overlapping)

    def _construct_body(self, element_attributes: Optional[bool] = False) -> Dict:
        """
        With TM1 10.2.2 Hierarchy and Element Attributes can't be created in one batch
        -> https://www.ibm.com/developerworks/community/forums/html/threadTopic?id=d91f3e0e-d305-44db-ac02-2fdcbee00393
        Thus, no need to have the ElementAttribute included in the JSON

        :param element_attributes: Only include element_attributes in body if explicitly asked for
        :return:
        """

        body_as_dict = collections.OrderedDict()
        body_as_dict["Name"] = self._name
        body_as_dict["Elements"] = []
        body_as_dict["Edges"] = []

        for element in self._elements.values():
            body_as_dict["Elements"].append(element.body_as_dict)
        for edge in self._edges:
            edge_as_dict = collections.OrderedDict()
            edge_as_dict["ParentName"] = edge[0]
            edge_as_dict["ComponentName"] = edge[1]
            edge_as_dict["Weight"] = self._edges[edge]
            body_as_dict["Edges"].append(edge_as_dict)
        if element_attributes:
            body_as_dict["ElementAttributes"] = [
                element_attribute.body_as_dict for element_attribute in self._element_attributes
            ]
        return body_as_dict

    def __iter__(self):
        return iter(self._elements.values())

    def __len__(self):
        return len(self._elements)

    def __contains__(self, item):
        return self.contains_element(item)

    def __getitem__(self, item):
        return self.get_element(item)
