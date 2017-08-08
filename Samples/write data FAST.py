import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

from TM1py.Objects import Cube, Dimension, Element, Hierarchy
from TM1py.Services import CubeService, DataService, DimensionService, LoginService, RESTService


# MDX Template
mdx_template = "SELECT " \
               "{{ SUBSET ([Big Dimension].Members, {}, {} ) }} on ROWS, " \
               "{{ [Python Cube Measure].[Numeric Element] }} on COLUMNS " \
               "FROM [Python Cube]"


# Setup everything if it doesnt already exist
def create_dimensions_and_cube():
    with RESTService('', 8001, LoginService.native('admin', 'apple'), ssl=False) as tm1_rest:
        dimension_service = DimensionService(tm1_rest)
        cube_service = CubeService(tm1_rest)

        # Build Measure Dimension
        element = Element('Numeric Element', 'Numeric')
        hierarchy1 = Hierarchy('Python Cube Measure', 'Python Cube Measure', [element])
        dimension1 = Dimension('Python Cube Measure', [hierarchy1])
        if not dimension_service.exists(dimension1.name):
            dimension_service.create(dimension1)

        # Build Index Dimension
        elements = [Element(str(num), 'Numeric') for num in range(1, 100000)]
        hierarchy2 = Hierarchy('Big Dimension', 'Big Dimension', elements)
        dimension2 = Dimension('Big Dimension', [hierarchy2])
        if not dimension_service.exists(dimension2.name):
            dimension_service.create(dimension2)

        cube = Cube('Python Cube', [dimension2.name, dimension1.name])
        if cube.name not in cube_service.get_all_names():
            cube_service.create(cube)


# Function to be called in parallel
def write_values(tm1, mdx, values):
    print('start with mdx: {}'.format(mdx))
    tm1.write_values_through_cellset(mdx=mdx, values=values)
    print('Done with mdx: {}'.format(mdx))


# Now fire requests asynchronously
async def main():
    loop = asyncio.get_event_loop()
    with RESTService('', 8001, LoginService.native('admin', 'apple'), ssl=False) as tm1_rest:
        data_service = DataService(tm1_rest)
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [loop.run_in_executor(executor, write_values, data_service,
                                            mdx_template.format(0, 9999), range(0, 9999)),
                       loop.run_in_executor(executor, write_values, data_service,
                                            mdx_template.format(9999, 19999), range(9999, 19999)),
                       loop.run_in_executor(executor, write_values, data_service,
                                            mdx_template.format(19999, 39999), range(19999, 29999)),
                       loop.run_in_executor(executor, write_values, data_service,
                                            mdx_template.format(29999, 49999), range(29999, 39999)),
                       loop.run_in_executor(executor, write_values, data_service,
                                            mdx_template.format(39999, 59999), range(39999, 49999)),
                       loop.run_in_executor(executor, write_values, data_service,
                                            mdx_template.format(49999, 69999), range(49999, 59999)),
                       loop.run_in_executor(executor, write_values, data_service,
                                            mdx_template.format(59999, 79999), range(59999, 69999)),
                       loop.run_in_executor(executor, write_values, data_service,
                                            mdx_template.format(69999, 89999), range(69999, 79999)),
                       loop.run_in_executor(executor, write_values, data_service,
                                            mdx_template.format(79999, 99999), range(79999, 89999)),
                       loop.run_in_executor(executor, write_values, data_service,
                                            mdx_template.format(89999, 99999), range(89999, 99999))]
            for future in futures:
                await future

# Create everything
create_dimensions_and_cube()

# Run it
start_time_total = time.time()
print("Starting")
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
run_time = time.time() - start_time_total
print('Time: {:.4f} sec'.format(run_time))
