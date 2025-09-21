# TM1py Documentation

<!-- markdownlint-disable MD033 -->
<div style="text-align: center;">
    <img alt="TM1py Logo" src="https://s3-ap-southeast-2.amazonaws.com/downloads.cubewise.com/web_assets/CubewiseLogos/TM1py-logo.png" style="width: 90%; height: 90%;text-align: center"/>  

    <img alt="PyPI - License" src="https://img.shields.io/pypi/l/TM1py">
    <img alt="PyPI - Version" src="https://img.shields.io/pypi/v/TM1py">
    <img alt="Pepy Total Downloads" src="https://img.shields.io/pepy/dt/TM1py">
</div>

Welcome to the **TM1py** documentation 🚀

## Why TM1py?

TM1py offers handy features to interact with TM1 from Python, such as

- Functions to read data from cubes through cube views or MDX queries (e.g. `tm1.cells.execute_mdx`)
- Functions to write data to cubes (e.g. `tm1.cells.write`)
- Functions to update dimensions and hierarchies (e.g. `tm1.hierarchies.get`)
- Functions to update metadata, clear or write to cubes directly from pandas dataframes  (e.g. `tm1.elements.get_elements_dataframe`)
- Async functions to easily parallelize your read or write operations (e.g. `tm1.cells.write_async`)
- Functions to execute TI process or loose statements of TI (e.g. `tm1.processes.execute_with_return`)
- CRUD features for all TM1 objects (cubes, dimensions, subsets, etc.)

## Explore the TM1py Documentation

- [Getting Started](getting-started.md)
- [How to Contribute](how-to-contribute.md)
- [Links](links.md)
- [API Reference](reference/summary.md)
