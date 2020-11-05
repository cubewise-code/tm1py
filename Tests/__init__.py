from Tests.Annotation import TestAnnotationMethods
from Tests.Application import TestApplicationMethods
from Tests.Cell import TestCellMethods
from Tests.Chore import TestChoreMethods
from Tests.Cube import TestCubeMethods
from Tests.Dimension import TestDimensionMethods
from Tests.Element import TestElementMethods
from Tests.Hierarchy import TestHierarchyMethods
from Tests.MDXUtils import TestMDXUtils
from Tests.MonitoringService import TestMonitoringMethods
from Tests.NativeView import TestNativeView
from Tests.PowerBiService import TestPowerBiService
from Tests.Process import TestProcessMethods
from Tests.RestService import TestRestServiceMethods
from Tests.Sandbox import TestSandboxMethods
from Tests.SandboxService import TestSandboxService
from Tests.Security import TestSecurityMethods
from Tests.Server import TestServerMethods
from Tests.Subset import TestSubsetMethods
from Tests.SubsetService import TestSubsetService
from Tests.TIObfuscator import TestTIObfuscatorMethods
from Tests.TM1pyDict import TestCaseAndSpaceInsensitiveDict, TestCaseAndSpaceInsensitiveSet, TestCaseAndSpaceInsensitiveTuplesDict
from Tests.Utils import TestUtilsMethods
from Tests.ViewService import TestViewService

""" Notes on TM1py Tests
- specify your instance coordinates in the config.ini file
- `EnableSandboxDimension` config parameter must be set to `F` for the target TM1 instance
- use PyCharm to run the pytests in this folder

"""
