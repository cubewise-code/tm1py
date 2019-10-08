from Tests.Annotation import TestAnnotationMethods
from Tests.Cell import TestDataMethods
from Tests.Chore import TestChoreMethods
from Tests.Cube import TestCubeMethods
from Tests.Dimension import TestDimensionMethods
from Tests.Element import TestElementMethods
from Tests.Hierarchy import TestHierarchyMethods
from Tests.Other import TestOtherMethods
from Tests.PowerBiService import TestPowerBiService
from Tests.Process import TestProcessMethods
from Tests.Security import TestSecurityMethods
from Tests.Server import TestServerMethods
from Tests.Subset import TestSubsetMethods
from Tests.Utils import TestTIObfuscatorMethods, TestMDXUtils
from Tests.View import TestViewMethods

""" Notes on TM1py Tests
- specify your instance coordinates in the config.ini file
- `EnableSandboxDimension` config parameter must be set to `F` for the target TM1 instance
- use PyCharm to run the pytests in this folder

"""
