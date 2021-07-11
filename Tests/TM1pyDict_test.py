import configparser
from pathlib import Path
import unittest

from TM1py.Services import TM1Service
from TM1py.Utils.Utils import CaseAndSpaceInsensitiveSet, CaseAndSpaceInsensitiveDict, CaseAndSpaceInsensitiveTuplesDict


class TestCaseAndSpaceInsensitiveDict(unittest.TestCase):
    tm1: TM1Service
    map: CaseAndSpaceInsensitiveDict

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates TM! objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath('config.ini'))
        cls.tm1 = TM1Service(**cls.config['tm1srv01'])
        
    @classmethod
    def setUp(cls):

        cls.map = CaseAndSpaceInsensitiveDict()
        cls.map["key1"] = "value1"
        cls.map["key2"] = "value2"
        cls.map["key3"] = "value3"

    @classmethod
    def tearDown(cls):
        del cls.map

    def test_set(self):
        self.map["key4"] = "value4"
        self.assertEqual(self.map["KEY4"], "value4")
        self.assertEqual(self.map["key4"], "value4")
        self.assertEqual(self.map["K e Y 4"], "value4")

    def test_get(self):
        self.assertEqual(self.map["KEY1"], "value1")
        self.assertEqual(self.map["key2"], "value2")
        self.assertEqual(self.map["K e Y 3"], "value3")

    def test_del(self):
        del self.map["KEY1"]
        del self.map["key2"]
        del self.map["K e Y 3"]

    def test_iter(self):
        for key1, key2 in zip(self.map, ("key1", "key2", "key3")):
            self.assertEqual(key1, key2)

    def test_len(self):
        self.assertEqual(3, len(self.map))

    def test_copy(self):
        c = self.map.copy()
        self.assertIsNot(c, self.map)
        self.assertEqual(c, self.map)

    def test_eq(self):
        _map = CaseAndSpaceInsensitiveDict()
        _map["key1"] = "value1"
        _map["key2"] = "value2"
        _map["key3"] = "value3"
        self.assertEqual(self.map, _map)

    def test_eq_case_and_space_insensitive(self):
        _map = CaseAndSpaceInsensitiveDict()
        _map["key1"] = "value1"
        _map["KEY2"] = "value2"
        _map["K e Y 3"] = "value3"
        self.assertEqual(self.map, _map)

    def test_ne(self):
        _map = CaseAndSpaceInsensitiveDict()
        _map["key 1"] = "wrong"
        _map["key 2"] = "value2"
        _map["key3"] = "value3"
        self.assertNotEqual(self.map, _map)

        _map = CaseAndSpaceInsensitiveDict()
        _map["key1"] = "value1"
        _map["key 2"] = "wrong"
        _map["key3"] = "value3"
        self.assertNotEqual(self.map, _map)

        _map = CaseAndSpaceInsensitiveDict()
        _map["key1"] = "value1"
        _map["key2"] = "value2"
        _map["key4"] = "value4"
        self.assertNotEqual(self.map, _map)


class TestCaseAndSpaceInsensitiveSet(unittest.TestCase):
    set: CaseAndSpaceInsensitiveSet

    @classmethod
    def setUp(cls):
        cls.original_values = ("Value1", "Value 2", "V A L U E 3")
        cls.set = CaseAndSpaceInsensitiveSet()
        cls.set.add(cls.original_values[0])
        cls.set.add(cls.original_values[1])
        cls.set.add(cls.original_values[2])

    @classmethod
    def tearDown(cls):
        del cls.set

    def test_get(self):
        self.assertIn("Value1", self.set)
        self.assertIn("VALUE1", self.set)
        self.assertIn("V ALUE 1", self.set)
        self.assertIn("Value2", self.set)
        self.assertIn("Value2", self.set)
        self.assertIn("V A L UE2", self.set)
        self.assertIn("Value3", self.set)
        self.assertIn("VALUE3", self.set)
        self.assertIn("V A LUE3", self.set)

        self.assertNotIn("Value", self.set)
        self.assertNotIn("VALUE4", self.set)
        self.assertNotIn("VA LUE 4", self.set)

    def test_del(self):
        del self.set["VALUE1"]
        del self.set["value2"]
        del self.set["V a L u E 3"]

    def test_discard(self):
        self.set.discard("Value1")
        self.set.discard("Value2")
        self.set.discard("Value3")
        # test for empty-ness
        self.assertFalse(self.set)

    def test_discard_case_and_space_insensitivity(self):
        self.set.discard("VAL UE 1")
        self.set.discard("Value2")
        self.set.discard("VA   LUE3")
        # test for empty-ness
        self.assertFalse(self.set)

    def test_len(self):
        self.set.add("Value4")
        self.assertEqual(4, len(self.set))
        self.set.discard("VALUE 4")
        self.assertEqual(3, len(self.set))

    def test_iter(self):
        self.assertEqual(len(self.set), len(self.original_values))
        for value in self.set:
            self.assertIn(value, self.original_values)

    def test_add(self):
        self.set.add("Value4")
        self.assertIn("Value4", self.set)
        self.assertIn("VALUE4", self.set)
        self.assertIn(" VALUE4", self.set)
        self.assertIn("VALUE4 ", self.set)
        self.assertIn("V ALUE 4", self.set)
        self.assertIn("Va L UE4", self.set)
        self.assertIn(" VAlue4", self.set)

    def test_copy(self):
        c = self.set.copy()
        self.assertIsNot(c, self.set)
        self.assertEqual(c, self.set)

    def test_eq(self):
        new_set = CaseAndSpaceInsensitiveSet()
        new_set.add(self.original_values[0])
        new_set.add(self.original_values[1])
        new_set.add(self.original_values[2])
        self.assertEqual(self.set, new_set)

    def test_eq_case_and_space_sensitivity(self):
        new_set = CaseAndSpaceInsensitiveSet()
        new_set.add(self.original_values[0].upper())
        new_set.add(self.original_values[1].lower())
        new_set.add(self.original_values[2].lower())
        self.assertEqual(self.set, new_set)

    def test_eq_against_set(self):
        new_set = set()
        new_set.add(self.original_values[0])
        new_set.add(self.original_values[1])
        new_set.add(self.original_values[2])
        self.assertEqual(self.set, new_set)

    def test_eq_against_set_case_and_space_sensitivity(self):
        new_set = set()
        new_set.add(self.original_values[0].upper())
        new_set.add(self.original_values[1].lower())
        new_set.add(self.original_values[2].upper())
        self.assertEqual(self.set, new_set)

    def test_ne(self):
        new_set = CaseAndSpaceInsensitiveSet()
        new_set.add("wrong1")
        new_set.add("wrong2")
        new_set.add("wrong3")
        self.assertNotEqual(self.set, new_set)

    def test_ne_against_set(self):
        new_set = set()
        new_set.add("wrong1")
        new_set.add("wrong2")
        new_set.add("wrong3")
        self.assertNotEqual(self.set, new_set)


class TestCaseAndSpaceInsensitiveTuplesDict(unittest.TestCase):
    tm1: TM1Service
    map: CaseAndSpaceInsensitiveTuplesDict

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to TM1 and creates TM! objects to use across all tests
        """

        # Connection to TM1
        config = configparser.ConfigParser()
        config.read(Path(__file__).parent.joinpath('config.ini'))
        cls.tm1 = TM1Service(**config['tm1srv01'])

    def setUp(self):
        self.map = CaseAndSpaceInsensitiveTuplesDict()
        self.map[("Elem1", "Elem1")] = "Value1"
        self.map[("Elem1", "Elem2")] = 2
        self.map[("Elem1", "Elem3")] = 3

    def tearDown(self):
        del self.map

    def test_del(self):
        self.assertIn(("Elem1", "Elem1"), self.map)
        self.assertIn(("Elem1", "Elem2"), self.map)
        self.assertIn(("Elem1", "Elem3"), self.map)
        del self.map[("El em1", "ELEM1")]
        del self.map[("El em1", "E L E M 2")]
        del self.map[("El em1", " eLEM3")]
        self.assertNotIn(("Elem1", "Elem1"), self.map)
        self.assertNotIn(("Elem1", "Elem2"), self.map)
        self.assertNotIn(("Elem1", "Elem3"), self.map)

    def test_eq(self):
        _map = CaseAndSpaceInsensitiveTuplesDict()
        _map[("Elem1", "Elem1")] = "Value1"
        _map[("Elem1", "Elem2")] = 2
        _map[("Elem1", "Elem3")] = 3
        self.assertEqual(_map, self.map)

        _map = CaseAndSpaceInsensitiveTuplesDict()
        _map[("Elem 1", "Elem1")] = "Value1"
        _map[("ELEM 1", "E L E M 2")] = 2
        _map[(" Elem1 ", "Elem 3")] = 3
        self.assertEqual(_map, self.map)

    def test_ne(self):
        _map = CaseAndSpaceInsensitiveTuplesDict()
        _map[("Elem1", "Elem1")] = "Value1"
        _map[("Elem1", "Elem2")] = 0
        _map[("Elem1", "Elem3")] = 3
        self.assertNotEqual(_map, self.map)

        _map = CaseAndSpaceInsensitiveTuplesDict()
        _map[("Elem 1", "Elem1")] = "Value1"
        _map[("ELEM 1", "E L E M 2")] = "wrong"
        _map[(" Elem1 ", "Elem 3")] = 3
        self.assertNotEqual(_map, self.map)

        _map = CaseAndSpaceInsensitiveTuplesDict()
        _map[("wrong", "Elem1")] = "Value1"
        _map[("Elem1", "Elem2")] = 2
        _map[("Elem1", "Elem3")] = 3
        self.assertNotEqual(_map, self.map)

    def test_get(self):
        self.assertEqual(self.map[("ELEM1", "ELEM1")], "Value1")
        self.assertEqual(self.map[("elem1", "e l e m 2")], 2)
        self.assertEqual(self.map[("e l e M 1", "elem3")], 3)
        self.assertNotEqual(self.map[("e l e M 1", "elem3")], 2)

    def test_iter(self):
        for tuple1, tuple2 in zip(self.map, [("Elem1", "Elem1"), ("Elem1", "Elem2"), ("Elem1", "Elem3")]):
            self.assertEqual(tuple1, tuple2)

    def test_len(self):
        self.assertEqual(len(self.map), 3)

    def test_set(self):
        self.map[("E L E M 1", "E L E M 2")] = 3
        self.assertEqual(self.map[("Elem1", "Elem2")], 3)

    def test_copy(self):
        c = self.map.copy()
        self.assertIsNot(c, self.map)
        self.assertEqual(c, self.map)

    def test_full(self):
        mdx_rows = '[}Clients].Members'
        mdx_columns = '[}Groups].Members'
        cube_name = '[}ClientGroups]'
        mdx = 'SELECT {} ON ROWS, {} ON COLUMNS FROM {}'.format(mdx_rows, mdx_columns, cube_name)
        data = self.tm1.cubes.cells.execute_mdx(mdx)

        # Get
        if self.tm1.version[0:2] == '10':
            coordinates = ('[}Clients].[ad min]', '[}Groups].[ADM IN]')
        else:
            coordinates = ('[}Clients].[}Clients].[ad min]', '[}Groups].[}Groups].[ADM IN]')
        self.assertIsNotNone(data[coordinates])

        # Delete
        if self.tm1.version[0:2] == '10':
            coordinates = ('[}clients].[}clients].[admin]', '[}groups].[}groups].[admin]')
        else:
            coordinates = ('[}clients].[}clients].[admin]', '[}groups].[}groups].[admin]')
        self.assertTrue(coordinates in data)
        del data[coordinates]
        self.assertFalse(coordinates in data)

        # Copy
        data_cloned = data.copy()
        self.assertTrue(data_cloned == data)
        self.assertFalse(data_cloned is data)

    @classmethod
    def tearDownClass(cls):
        cls.tm1.logout()


if __name__ == '__main__':
    unittest.main()
