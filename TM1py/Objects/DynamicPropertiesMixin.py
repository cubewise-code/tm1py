# -*- coding: utf-8 -*-

from typing import Dict, Optional


class DynamicPropertiesMixin:
    """Mixin that adds support for dynamic/extra properties from the TM1 REST API.

    TM1 objects can carry additional properties beyond their known fields.
    This mixin provides a common interface to store, filter, and serialize them.

    Subclasses must define ``_DYNAMIC_PROPERTIES_EXCLUDED_KEYS`` as a frozenset
    of keys that are already handled explicitly (e.g. "Name", "@odata.type").
    """

    _DYNAMIC_PROPERTIES_EXCLUDED_KEYS: frozenset = frozenset()

    @property
    def dynamic_properties(self) -> Dict:
        return self._dynamic_properties

    @dynamic_properties.setter
    def dynamic_properties(self, value: Optional[Dict]) -> None:
        self._dynamic_properties = value or {}

    @classmethod
    def _filter_dynamic_properties(cls, properties: Dict) -> Dict:
        """Return a copy of *properties* with all reserved/excluded keys removed."""
        return {k: v for k, v in properties.items() if k not in cls._DYNAMIC_PROPERTIES_EXCLUDED_KEYS}
