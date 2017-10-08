"""
A python module for TM1.

https://github.com/MariusWirtz-cubewise/TM1py

TM1py wraps the TM1 REST API into concise Python classes and Services that simplify TM1 interactions from python.

Usage:
>>> with RESTService(address='', port=8001, user='admin', password='apple', ssl=False) as tm1_rest:
>>>     subset_service = SubsetService(tm1_rest)
>>>     subset = Subset(dimension_name='Month', subset_name='Q1', elements=['Jan', 'Feb', 'Mar'])
>>>     subset_service.create(subset, private=True)

"""


# __init__ can hoist attributes from submodules into higher namespaces for convenience

from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RESTService import RESTService
from TM1py.Services.TM1Service import TM1Service
from TM1py.Services.AnnotationService import AnnotationService
from TM1py.Services.ChoreService import ChoreService
from TM1py.Services.CubeService import CubeService
from TM1py.Services.CellService import CellService
from TM1py.Services.DimensionService import DimensionService
from TM1py.Services.ElementService import ElementService
from TM1py.Services.HierarchyService import HierarchyService
from TM1py.Services.ServerService import ServerService
from TM1py.Services.ProcessService import ProcessService
from TM1py.Services.SubsetService import SubsetService
from TM1py.Services.MonitoringService import MonitoringService
from TM1py.Services.SecurityService import SecurityService
from TM1py.Services.ViewService import ViewService

from TM1py.Objects.Annotation import Annotation
from TM1py.Objects.Axis import ViewAxisSelection, ViewTitleSelection
from TM1py.Objects.Chore import Chore
from TM1py.Objects.ChoreFrequency import ChoreFrequency
from TM1py.Objects.ChoreStartTime import ChoreStartTime
from TM1py.Objects.ChoreTask import ChoreTask
from TM1py.Objects.Cube import Cube
from TM1py.Objects.Dimension import Dimension
from TM1py.Objects.Element import Element
from TM1py.Objects.ElementAttribute import ElementAttribute
from TM1py.Objects.Hierarchy import Hierarchy
from TM1py.Objects.MDXView import MDXView
from TM1py.Objects.NativeView import NativeView
from TM1py.Objects.Process import Process
from TM1py.Objects.Rules import Rules
from TM1py.Objects.Server import Server
from TM1py.Objects.Subset import Subset, AnonymousSubset
from TM1py.Objects.User import User
from TM1py.Objects.View import View

from TM1py.Utils import Utils
