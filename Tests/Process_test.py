import unittest

from TM1py.Objects import BreakPointType, HitMode


class TestBreakPointType(unittest.TestCase):

    def test_BreakPointType_init(self):
        break_point_type = BreakPointType("ProcessDebugContextDataBreakpoint")
        self.assertEqual(BreakPointType.PROCESS_DEBUG_CONTEXT_DATA_BREAK_POINT, break_point_type)

    def test_BreakPointType_init_case(self):
        break_point_type = BreakPointType("ProcessDebugContextDataBREAKPOINT")
        self.assertEqual(BreakPointType.PROCESS_DEBUG_CONTEXT_DATA_BREAK_POINT, break_point_type)

    def test_BreakPointType_str(self):
        break_point_type = BreakPointType.PROCESS_DEBUG_CONTEXT_DATA_BREAK_POINT
        self.assertEqual("ProcessDebugContextDataBreakpoint", str(break_point_type))


class TestHitMode(unittest.TestCase):

    def test_HitMode_init(self):
        hit_mode = HitMode("BreakAlways")
        self.assertEqual(HitMode.BREAK_ALWAYS, hit_mode)

    def test_BreakPointType_init_case(self):
        hit_mode = HitMode("BreakAlways")
        self.assertEqual(HitMode.BREAK_ALWAYS, hit_mode)

    def test_BreakPointType_str(self):
        hit_mode = HitMode.BREAK_ALWAYS
        self.assertEqual("BreakAlways", str(hit_mode))
