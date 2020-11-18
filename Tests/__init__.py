from Tests.AnnotationService import TestAnnotationService
from Tests.ApplicationService import TestApplicationService
from Tests.CellService import TestCellService
from Tests.ChoreService import TestChoreService
from Tests.CubeService import TestCubeService
from Tests.DimensionService import TestDimensionService
from Tests.Element import TestElement
from Tests.ElementAttribute import TestElementAttribute
from Tests.ElementService import TestElementService
from Tests.HierarchyService import TestHierarchyService
from Tests.MDXUtils import TestMDXUtils
from Tests.MonitoringService import TestMonitoringService
from Tests.NativeView import TestNativeView
from Tests.PowerBiService import TestPowerBiService
from Tests.ProcessService import TestProcessService
from Tests.RestService import TestRestService
from Tests.Sandbox import TestSandboxMethods
from Tests.SandboxService import TestSandboxService
from Tests.SecurityService import TestSecurityService
from Tests.ServerService import TestServerService
from Tests.Subset import TestSubset
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
