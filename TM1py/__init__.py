"""
A python module for TM1.

https://github.com/cubewise-code/TM1py

TM1py wraps the TM1 REST API into concise Python classes and Services that simplify TM1 interactions from python.

Usage:
>>> with RestService(address='', port=8001, user='admin', password='apple', ssl=False) as tm1_rest:
>>>     subset_service = SubsetService(tm1_rest)
>>>     subset = Subset(dimension_name='Month', subset_name='Q1', elements=['Jan', 'Feb', 'Mar'])
>>>     subset_service.create(subset, private=True)

"""

# __init__ can hoist attributes from submodules into higher namespaces for convenience

from TM1py.Objects.Annotation import Annotation
from TM1py.Objects.Application import Application
from TM1py.Objects.Axis import ViewAxisSelection, ViewTitleSelection
from TM1py.Objects.Chore import Chore
from TM1py.Objects.ChoreFrequency import ChoreFrequency
from TM1py.Objects.ChoreStartTime import ChoreStartTime
from TM1py.Objects.ChoreTask import ChoreTask
from TM1py.Objects.Cube import Cube
from TM1py.Objects.Dimension import Dimension
from TM1py.Objects.Element import Element
from TM1py.Objects.ElementAttribute import ElementAttribute
from TM1py.Objects.Git import Git
from TM1py.Objects.GitCommit import GitCommit
from TM1py.Objects.GitPlan import GitPlan
from TM1py.Objects.GitRemote import GitRemote
from TM1py.Objects.Hierarchy import Hierarchy
from TM1py.Objects.MDXView import MDXView
from TM1py.Objects.NativeView import NativeView
from TM1py.Objects.Process import Process
from TM1py.Objects.Rules import Rules
from TM1py.Objects.Sandbox import Sandbox
from TM1py.Objects.Server import Server
from TM1py.Objects.Subset import Subset, AnonymousSubset
from TM1py.Objects.User import User
from TM1py.Objects.View import View
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Services.AnnotationService import AnnotationService
from TM1py.Services.ApplicationService import ApplicationService
from TM1py.Services.CellService import CellService
from TM1py.Services.ChoreService import ChoreService
from TM1py.Services.CubeService import CubeService
from TM1py.Services.DimensionService import DimensionService
from TM1py.Services.ElementService import ElementService
from TM1py.Services.FileService import FileService
from TM1py.Services.GitService import GitService
from TM1py.Services.HierarchyService import HierarchyService
from TM1py.Services.ProcessService import ProcessService
from TM1py.Services.SandboxService import SandboxService
from TM1py.Services.SecurityService import SecurityService
from TM1py.Services.SubsetService import SubsetService
from TM1py.Services.TM1Service import TM1Service
from TM1py.Services.ViewService import ViewService
from TM1py.Services.ManageService import ManageService
from TM1py.Services.JobService import JobService
from TM1py.Services.UserService import UserService
from TM1py.Services.ThreadService import ThreadService
from TM1py.Services.SessionService import SessionService
from TM1py.Services.TransactionLogService import TransactionLogService
from TM1py.Services.MessageLogService import MessageLogService
from TM1py.Services.ConfigurationService import ConfigurationService
from TM1py.Services.AuditLogService import AuditLogService

from TM1py.Services.ServerService import ServerService
from TM1py.Services.PowerBiService import PowerBiService
from TM1py.Services.MonitoringService import MonitoringService

from TM1py.Utils import Utils
from TM1py.Services.JobService import JobService

__version__ = "2.1"
