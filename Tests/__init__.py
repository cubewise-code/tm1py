# The commented-out- tests fail in TM1 Version 11 due to a bug in the TM1 Server:
# https://www.ibm.com/developerworks/community/forums/html/topic?id=75f2b99e-6961-4c71-9364-1d5e1e083eff

#from Tests.Annotation import TestAnnotationMethods
from Tests.Chore import TestChoreMethods
from Tests.Cube import TestCubeMethods
from Tests.Data import TestDataMethods
from Tests.Dimension import TestDimensionMethods
#from Tests.Hierarchy import TestHierarchyMethods
from Tests.Utils import TestTIObfuscatorMethods, TestMDXUtils
from Tests.Other import TestOtherMethods
from Tests.Process import TestProcessMethods
from Tests.Security import TestSecurityMethods
from Tests.Server import TestServerMethods
from Tests.Subset import TestSubsetMethods

from Tests.View import TestViewMethods
