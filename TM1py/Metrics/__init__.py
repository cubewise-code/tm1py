"""Pure, server-free building blocks behind ``tm1.metrics`` (MetricService).

These modules hold the tricky logic (vocabulary mapping, MDX building, OData
``$filter`` building, record shaping) so it can be unit-tested without a live
TM1 server. The thin :class:`TM1py.Services.MetricService.MetricService`
orchestrates version dispatch and REST I/O and delegates to them.
"""
