import collections


def read_cube_name_from_mdx(mdx):
    """ Read the cubename from a valid MDX Query

    :param mdx: The MDX Query as String
    :return: String, name of a cube
    """

    mdx_trimed = ''.join(mdx.split()).upper()
    post_start = mdx_trimed.rfind("FROM[") + len("FROM[")
    pos_end = mdx_trimed.find("]WHERE", post_start)
    # if pos_end is -1 it works too
    cube_name = mdx_trimed[post_start:pos_end]
    return cube_name


def construct_mdx_axis(dim_selections):
    """ Construct MDX for one Axis (Row or Column).
    Can have multiple dimensions stacked.

    :param dim_selections: Dictionary of the Dimension Name and a selection (Dimension-MDX, List of Elementnames, 
    Subset, or None)
    :return: a valid MDX for an Axis
    """
    mdx_selection = ''
    for dim, selection in dim_selections.items():
        # import if the MDX is defined directly as a string
        if isinstance(selection, str) and selection.find('subset(') == -1:
            mdx_selection += '*' + selection
        # scan for subset() and generate subset syntax
        elif isinstance(selection, str) and selection.find('subset(') == 0:
            mdx_selection += '*' + 'TM1SubsetToSet([{}],\"{}\")'.format(dim, selection[7:-1])
        # default to get all elements if selection is empty
        elif not selection:
            mdx_selection += '*' + '{' + 'TM1SubsetAll([{}])'.format(dim) + '}'
        # iterate and add all elements
        elif isinstance(selection, collections.Iterable):
            mdx_selection += '*{'
            for element in selection:
                mdx_selection += '[{}].[{}],'.format(dim, element)
            mdx_selection = mdx_selection[:-1] + '}'
    return mdx_selection[1:]


def construct_mdx(cube_name, rows, columns, contexts=None, suppress=None):
    """ Method to construct MDX Query from 

    :param cube_name: Name of the Cube 
    :param rows: Dictionary of Dimension Names and Selections
    :param columns: Dictionary of Dimension Names and Selections (Dimension-MDX, List of Elementnames, Subset, or None)
    :param contexts: Dictionary of Dimension Names and Selections
    :param suppress: "Both", "Rows", "Columns" or None
    :return: Genered MDX Query
    """

    # MDX Skeleton
    mdx_template = 'SELECT {}{} ON ROWS, {}{} ON COLUMNS FROM [{}] {}'

    # Suppression
    mdx_rows_suppress = 'NON EMPTY ' if (suppress in ['Rows', 'Both'] and rows) else ''
    mdx_columns_suppress = 'NON EMPTY ' if (suppress in ['Columns', 'Both'] and columns) else ''

    # Rows and Columns
    mdx_rows = construct_mdx_axis(rows)
    mdx_columns = construct_mdx_axis(columns)

    # Context filter (where statement)
    mdx_where = ''
    if contexts:
        mdx_where_parts = ['[{}].[{}]'.format(dim, elem) for dim, elem in contexts.items()]
        mdx_where += "WHERE (" + ','.join(mdx_where_parts) + ")"

    # Return Full MDX
    return mdx_template.format(mdx_rows_suppress, mdx_rows, mdx_columns_suppress, mdx_columns, cube_name, mdx_where)


