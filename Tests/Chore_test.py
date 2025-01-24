import unittest
 
from TM1py import Chore, ChoreStartTime, ChoreFrequency, ChoreTask
from TM1py.Objects import Chore
 
class TestChore(unittest.TestCase): 
    def setUp(self):
        self.chore = Chore(
        name="chore",
        start_time=ChoreStartTime(2023, 8, 4, 10, 0, 0),
        dst_sensitivity=False,
        active=True,
        execution_mode="SingleCommit",
        frequency=ChoreFrequency(1, 0, 0, 0),
        tasks=[
            ChoreTask(
                step=0,
                process_name="}bedrock.server.wait",
                parameters=[
                    {'Name': 'pLogOutput', 'Value': 0},
                    {'Name': 'pStrictErrorHandling', 'Value': 1},
                    {'Name': 'pWaitSec', 'Value': 4}]),
            ChoreTask(
                step=1,
                process_name="}bedrock.server.wait",
                parameters=[
                    {'Name': 'pLogOutput', 'Value': 0},
                    {'Name': 'pStrictErrorHandling', 'Value': 1},
                    {'Name': 'pWaitSec', 'Value': 5}]),
        ])

    def test_from_dict_and_construct_body(self):
        text = self.chore.body
 
        chore = Chore.from_json(text)
 
        self.assertEqual(self.chore, chore)
 
    def test_insert_task_as_step_0(self):
        self.chore.insert_task(
            ChoreTask(
                step=0,
                process_name="}bedrock.cube.clone",
                parameters=[
                    {'Name': 'pLogOutput', 'Value': 0},
                    {'Name': 'pStrictErrorHandling', 'Value': 1},
                    {'Name': 'pWaitSec', 'Value': 5}]))
        expected_chore = Chore(
        name="chore",
        start_time=ChoreStartTime(2023, 8, 4, 10, 0, 0),
        dst_sensitivity=False,
        active=True,
        execution_mode="SingleCommit",
        frequency=ChoreFrequency(1, 0, 0, 0),
        tasks=[
            ChoreTask(
                step=0,
                process_name="}bedrock.cube.clone",
                parameters=[
                    {'Name': 'pLogOutput', 'Value': 0},
                    {'Name': 'pStrictErrorHandling', 'Value': 1},
                    {'Name': 'pWaitSec', 'Value': 5}]),
            ChoreTask(
                step=1,
                process_name="}bedrock.server.wait",
                parameters=[
                    {'Name': 'pLogOutput', 'Value': 0},
                    {'Name': 'pStrictErrorHandling', 'Value': 1},
                    {'Name': 'pWaitSec', 'Value': 4}]),

            ChoreTask(
                step=2,
                process_name="}bedrock.server.wait",
                parameters=[
                    {'Name': 'pLogOutput', 'Value': 0},
                    {'Name': 'pStrictErrorHandling', 'Value': 1},
                    {'Name': 'pWaitSec', 'Value': 5}]),
        ])
        self.assertEqual(self.chore, expected_chore)
 
    def test_insert_task_as_step_1(self):
        self.chore.insert_task(
            ChoreTask(
                step=1,
                process_name="}bedrock.cube.clone",
                parameters=[
                    {'Name': 'pLogOutput', 'Value': 0},
                    {'Name': 'pStrictErrorHandling', 'Value': 1},
                    {'Name': 'pWaitSec', 'Value': 5}]))
        expected_chore = Chore(
        name="chore",
        start_time=ChoreStartTime(2023, 8, 4, 10, 0, 0),
        dst_sensitivity=False,
        active=True,
        execution_mode="SingleCommit",
        frequency=ChoreFrequency(1, 0, 0, 0),
        tasks=[
            ChoreTask(
                step=0,
                process_name="}bedrock.server.wait",
                parameters=[
                    {'Name': 'pLogOutput', 'Value': 0},
                    {'Name': 'pStrictErrorHandling', 'Value': 1},
                    {'Name': 'pWaitSec', 'Value': 4}]),
            ChoreTask(
                step=1,
                process_name="}bedrock.cube.clone",
                parameters=[
                    {'Name': 'pLogOutput', 'Value': 0},
                    {'Name': 'pStrictErrorHandling', 'Value': 1},
                    {'Name': 'pWaitSec', 'Value': 5}]),
            ChoreTask(
                step=2,
                process_name="}bedrock.server.wait",
                parameters=[
                    {'Name': 'pLogOutput', 'Value': 0},
                    {'Name': 'pStrictErrorHandling', 'Value': 1},
                    {'Name': 'pWaitSec', 'Value': 5}]),
        ])
        self.assertEqual(self.chore, expected_chore)
       
 
if __name__ == '__main__':
    unittest.main()
 
 