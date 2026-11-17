"""Generates the TI processes that move cube data through files in the TM1 file store ("blobs").

This module is the single place where every decision about generated blob TI lives. It makes no REST calls: the
caller gathers the facts once (a ``CubeProfile``) and describes what to export or load (an ``ExportSpec`` or a
``LoadSpec``), and the builder returns a ``Process`` ready to execute.

Two modes:

- **legacy** (``lean=False``) reproduces the TI TM1py has always generated, character for character. It is the
  default on every existing ``use_blob`` path.
- **lean** (``lean=True``) contains only the code a given cube needs, decided when the process is generated:
  no per-row quote escaping unless a dimension or a string measure needs it, a single ``CellPutN`` for numeric
  cubes, and so on.

Encoding: v11 applies ``SetOutputCharacterSet`` only to the procedure it is called in, and writes a BOM when the
output is UTF-8. An export therefore sets the character set on the first data record, and on v11 the file starts
with a BOM. v12 always writes UTF-8 without a BOM.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, FrozenSet, List, Mapping, Optional, Tuple

from TM1py.Objects.Process import Process
from TM1py.Utils.Utils import lower_and_drop_spaces

ELEMENT_ATTRIBUTES_PREFIX = "}elementattributes_"

# legacy TI has trailing spaces on some lines; written explicitly so editors and formatters keep them
_SPACE = " "

# above this many string measures, the lean load branches on the element type instead of on element names
MAX_STRING_MEASURES_BY_NAME = 20

# long strings (MDX) are assigned to a TI variable in pieces of this many characters
TI_STRING_PIECE_LENGTH = 4000


def _normalize(name: str) -> str:
    return lower_and_drop_spaces(name)


def ti_string(value: str) -> str:
    """Return ``value`` as a TI string literal, with embedded single quotes doubled."""
    return "'" + str(value).replace("'", "''") + "'"


def _legacy_string(value: str) -> str:
    """TI string literal as legacy TM1py wrote it: quoted, never escaped."""
    return f"'{value}'"


def ti_file_name(file_name: str, is_v12: bool) -> str:
    """The name a TI process must use for a file created through the contents API.

    v11 stores such documents with an extra ``.blb`` extension.
    """
    return file_name if is_v12 else file_name + ".blb"


def enable_sandbox_ti(sandbox_name: Optional[str], sandboxing_disabled: bool) -> str:
    """TI that activates ``sandbox_name``, or the base, for the rest of the process."""
    if sandboxing_disabled:
        return ""
    if sandbox_name:
        return f"ServerActiveSandboxSet('{sandbox_name}');SetUseActiveSandboxProperty(1);"
    return "ServerActiveSandboxSet('');SetUseActiveSandboxProperty(0);"


@dataclass(frozen=True)
class CubeProfile:
    """Facts about one cube on one server, gathered once per call.

    :param cube_name: name of the cube
    :param dimensions: dimension names in the cube's natural order; the last one is the measure dimension
    :param is_v12: whether the server is v12 or later
    :param sandboxing_disabled: whether sandboxing is disabled on the server
    :param string_measures: elements of the measure dimension that are of type String
    :param quoted_dimensions: dimensions with the quote character in at least one exported element name
    """

    cube_name: str
    dimensions: Tuple[str, ...]
    is_v12: bool = False
    sandboxing_disabled: bool = False
    string_measures: FrozenSet[str] = frozenset()
    quoted_dimensions: FrozenSet[str] = frozenset()

    def __post_init__(self):
        object.__setattr__(self, "dimensions", tuple(self.dimensions))
        object.__setattr__(self, "string_measures", frozenset(self.string_measures))
        object.__setattr__(self, "quoted_dimensions", frozenset(_normalize(d) for d in self.quoted_dimensions))

    @property
    def is_attribute_cube(self) -> bool:
        return self.cube_name.lower().startswith(ELEMENT_ATTRIBUTES_PREFIX)

    @property
    def measure_dimension(self) -> str:
        return self.dimensions[-1]

    def has_quotes(self, dimension: str) -> bool:
        return _normalize(dimension) in self.quoted_dimensions


@dataclass(frozen=True)
class CsvLayout:
    """Shape of the file written by an export or read by a load.

    :param delimiter: field delimiter
    :param quote_character: character that encloses every field; empty for none
    :param header: column labels for a header line, without the value column's label; empty for no header line
    :param value_header: label of the value column in the header line
    """

    delimiter: str = ","
    quote_character: str = '"'
    header: Tuple[str, ...] = ()
    value_header: str = "Value"

    def __post_init__(self):
        object.__setattr__(self, "header", tuple(self.header))


@dataclass(frozen=True)
class SourceVariable:
    """A variable of the export's view data source, in data source order.

    :param name: TI variable name
    :param dimension: dimension the variable holds elements of
    :param hierarchy: hierarchy the variable holds elements of; defaults to the dimension's same-named hierarchy
    :param column: 1-based position in the file; ``None`` for a variable that is not written (a title)
    """

    name: str
    dimension: str
    hierarchy: Optional[str] = None
    column: Optional[int] = None

    @property
    def hierarchy_name(self) -> str:
        return self.hierarchy or self.dimension


@dataclass(frozen=True)
class ExportSpec:
    """What an export process reads and where it writes.

    :param process_name: name of the (unbound) process
    :param file_name: file in the file store, as created through the contents API (no ``.blb``)
    :param view_name: name of the view that is the data source
    :param variables: data source variables in data source order. For a view built from ``view_definition``:
        cube order for a native view; for an MDX view, the column dimensions, then the row dimensions, then every
        other dimension in cube order
    :param aliases: dimension name -> alias attribute written instead of the element name (lean only)
    :param view_definition: a ``NativeView`` or an MDX string (lean only). The prolog builds it as the temporary
        view ``view_name``. Otherwise ``view_name`` must exist when the process runs
    """

    process_name: str
    file_name: str
    view_name: str
    variables: Tuple[SourceVariable, ...]
    skip_zeros: bool = True
    skip_consolidated_cells: bool = True
    skip_rule_derived_cells: bool = True
    top: Optional[int] = None
    skip: Optional[int] = None
    sandbox_name: Optional[str] = None
    aliases: Mapping[str, str] = field(default_factory=dict)
    view_definition: Any = None

    def __post_init__(self):
        object.__setattr__(self, "variables", tuple(self.variables))

    @property
    def written_variables(self) -> List[SourceVariable]:
        return sorted((v for v in self.variables if v.column is not None), key=lambda v: v.column)


@dataclass(frozen=True)
class LoadSpec:
    """How a load process writes a file into the profile's cube.

    :param process_name: name of the (unbound) process
    :param file_name: file in the file store, as created through the contents API (no ``.blb``)
    :param clear_view: name of a view on the cube to zero out before loading
    """

    process_name: str
    file_name: str
    increment: bool = False
    skip_non_updateable: bool = False
    allow_spread: bool = False
    sandbox_name: Optional[str] = None
    clear_view: Optional[str] = None


# ---------------------------------------------------------------------------------------------------------------- #
# export
# ---------------------------------------------------------------------------------------------------------------- #


def build_export_process(profile: CubeProfile, layout: CsvLayout, spec: ExportSpec, lean: bool = False) -> Process:
    """Build an unbound process that writes the cells of ``spec.view_name`` to ``spec.file_name``.

    Every variable is written in ``column`` order, followed by the cell value (``SVALUE``).
    """
    process = Process(
        name=spec.process_name,
        datasource_type="TM1CubeView",
        datasource_view=spec.view_name,
        datasource_data_source_name_for_server=profile.cube_name,
        datasource_data_source_name_for_client=profile.cube_name,
        datasource_ascii_delimiter_char=layout.delimiter,
        datasource_ascii_decimal_separator=".",
        datasource_ascii_thousand_separator="",
    )
    for variable in spec.variables:
        process.add_variable(name=variable.name, variable_type="String")

    file_name = ti_file_name(spec.file_name, profile.is_v12)
    if spec.view_definition is not None and not lean:
        raise ValueError("A view built in the export process (view_definition) requires lean TI")
    if lean:
        process.prolog_procedure = _lean_export_prolog(profile, layout, spec, file_name)
        process.data_procedure = _lean_export_data(profile, layout, spec, file_name)
    else:
        process.prolog_procedure = _legacy_export_prolog(profile, layout, spec)
        process.data_procedure = _legacy_export_data(profile, layout, spec, file_name)
    return process


def _view_extract_settings(cube: str, view: str, spec: ExportSpec, string: Callable[[str], str]) -> List[str]:
    return [
        f"ViewExtractSkipCalcsSet({string(cube)}, {string(view)}, {'1' if spec.skip_consolidated_cells else '0'});",
        f"ViewExtractSkipRuleValuesSet({string(cube)}, {string(view)}, {'1' if spec.skip_rule_derived_cells else '0'});",
        f"ViewExtractSkipZeroesSet({string(cube)}, {string(view)}, {'1' if spec.skip_zeros else '0'});",
    ]


def _escape_quotes_ti(variable: str, quote_character: str, indent: str = "") -> str:
    """TI that doubles every ``quote_character`` in ``variable``."""
    escaped_quote = quote_character.replace("'", "''")
    lines = [
        f"IF (SCAN('{escaped_quote}', {variable}) > 0);",
        f"  sTextToEscape = {variable};",
        "  nPos = LONG(sTextToEscape);",
        "  WHILE (nPos > 0);",
        f"    IF (SUBST(sTextToEscape, nPos, 1) @= '{escaped_quote}');",
        f"      sTextToEscape = INSRT('{escaped_quote}', sTextToEscape, nPos);",
        "    ENDIF;",
        "    nPos = nPos - 1;",
        "  END;",
        f"  {variable} = sTextToEscape;",
        "ENDIF;",
    ]
    return "\n".join(indent + line for line in lines)


def _legacy_export_prolog(profile: CubeProfile, layout: CsvLayout, spec: ExportSpec) -> str:
    cube, view = profile.cube_name, spec.view_name
    return f"""
        {enable_sandbox_ti(spec.sandbox_name, profile.sandboxing_disabled)}
        ViewExtractSkipCalcsSet('{cube}', '{view}', {'1' if spec.skip_consolidated_cells else '0'});
        ViewExtractSkipRuleValuesSet('{cube}', '{view}', {'1' if spec.skip_rule_derived_cells else '0'});
        ViewExtractSkipZeroesSet('{cube}', '{view}', {'1' if spec.skip_zeros else '0'});
        DatasourceAsciiDelimiter='{layout.delimiter}';
        DatasourceAsciiQuoteCharacter='{layout.quote_character}';
        DatasourceASCIIDecimalSeparator='.';
        nRecord=0;
        """


def _legacy_header_line(layout: CsvLayout) -> str:
    if not layout.header:
        return ""
    return ",".join(_legacy_string(label) for label in (*layout.header, layout.value_header))


def _legacy_export_data(profile: CubeProfile, layout: CsvLayout, spec: ExportSpec, file_name: str) -> str:
    header_line = _legacy_header_line(layout)
    top, skip = spec.top, spec.skip
    output_variables = [variable.name for variable in spec.written_variables]
    comma_sep_variables = ",".join(output_variables)

    data_procedure_pre = f"""
        IF (nRecord = 0);
          SetOutputCharacterSet('{file_name}','TM1CS_UTF8');
        ENDIF;
        nRecord = nRecord + 1;
        """
    if header_line:
        data_procedure_pre += f"""
            IF (nRecord = 1);
              TextOutput('{file_name}',{header_line});
            ENDIF;
            """
    if top:
        if skip:
            top += skip
        data_procedure_pre += f"""
            IF (nRecord > {top});
              ProcessBreak;
            ENDIF;
            """
    if skip:
        data_procedure_pre += f"""
            IF (nRecord <= {skip});
              ItemSkip;
            ENDIF;
            """

    # v12 occasionally produces tiny numbers (e.g. 4.94066e-324) instead of 0
    if profile.is_v12:
        data_procedure_pre += f"""
            IF (ISUNDEFINEDCELLVALUE(NVALUE,'{profile.cube_name}') = 1);
              SVALUE ='0';
            ENDIF;
            """

    for variable in output_variables + ["SVALUE"]:
        data_procedure_pre += f"""
            sTextToEscape = {variable};
            sEscapeChar = '"';
            IF (SCAN(sEscapeChar, sTextToEscape) > 0);
                nPos = LONG ( sTextToEscape );
                WHILE ( nPos > 0);
                    sChar = Subst(sTextToEscape, nPos, 1);
                    IF ( sChar @= sEscapeChar );
                      sTextToEscape = INSRT(sEscapeChar, sTextToEscape, nPos);
                    ENDIF;{_SPACE * 2}
                    nPos = nPos - 1;
                END;
                {variable} = sTextToEscape;
            ENDIF;
            """

    data_procedure = f"""
        TextOutput('{file_name}',{comma_sep_variables},SVALUE);
        """
    return data_procedure_pre + data_procedure


def _lean_header_ti(file_name: str, layout: CsvLayout) -> str:
    labels = ",".join(ti_string(label) for label in (*layout.header, layout.value_header))
    return f"TextOutput({ti_string(file_name)},{labels});"


def _lean_export_prolog(profile: CubeProfile, layout: CsvLayout, spec: ExportSpec, file_name: str) -> str:
    lines = _view_build_ti(profile, spec)
    sandbox = enable_sandbox_ti(spec.sandbox_name, profile.sandboxing_disabled)
    if sandbox:
        lines.append(sandbox)
    lines += _view_extract_settings(profile.cube_name, spec.view_name, spec, ti_string)
    lines += [
        f"DatasourceAsciiDelimiter={ti_string(layout.delimiter)};",
        f"DatasourceAsciiQuoteCharacter={ti_string(layout.quote_character)};",
        "DatasourceASCIIDecimalSeparator='.';",
    ]
    lines.append("nRecord = 0;")
    if spec.top or spec.skip:
        lines.append("nCell = 0;")
    return "\n".join(lines) + "\n"


def ti_string_assignment(variable: str, value: str, piece_length: int = TI_STRING_PIECE_LENGTH) -> List[str]:
    """TI that assigns ``value`` to ``variable``, concatenated from pieces so no literal gets too long."""
    pieces = [value[i : i + piece_length] for i in range(0, len(value), piece_length)] or [""]
    return [f"{variable} = {ti_string(pieces[0])};"] + [
        f"{variable} = {variable} | {ti_string(piece)};" for piece in pieces[1:]
    ]


def _mdx_name(name: str) -> str:
    return name.replace("]", "]]")


def _view_build_ti(profile: CubeProfile, spec: ExportSpec) -> List[str]:
    """TI that builds ``spec.view_definition`` as the temporary view ``spec.view_name``. Temporary objects are
    removed by the server when the process ends, whether it succeeds or not."""
    definition = spec.view_definition
    if definition is None:
        return []
    cube, view = ti_string(profile.cube_name), ti_string(spec.view_name)
    if isinstance(definition, str):
        return ti_string_assignment("sMdx", definition) + [f"ViewCreateByMDX({cube}, {view}, sMdx, 1);"]
    return _native_view_build_ti(profile, definition, cube, view)


def _native_view_build_ti(profile: CubeProfile, native_view, cube: str, view: str) -> List[str]:
    """One temporary subset per cube dimension, in cube order. A dimension the view doesn't mention gets its
    default member, as it would in MDX."""
    cube_dimensions = {_normalize(dimension): dimension for dimension in profile.dimensions}
    selections = {}
    for selection in (*native_view.columns, *native_view.rows, *native_view.titles):
        key = _normalize(selection.dimension_name)
        if key not in cube_dimensions:
            raise ValueError(f"Dimension '{selection.dimension_name}' is not in cube '{profile.cube_name}'")
        selections[key] = selection

    lines = [f"ViewCreate({cube}, {view}, 1);"]
    for position, dimension in enumerate(profile.dimensions, start=1):
        selection = selections.get(_normalize(dimension))
        subset = getattr(selection, "subset", None)
        if subset is not None and _normalize(subset.hierarchy_name or dimension) != _normalize(dimension):
            raise NotImplementedError(
                f"Alternate hierarchy '{dimension}:{subset.hierarchy_name}' in a native view built in TI"
            )

        dimension_literal = ti_string(dimension)
        subset_name = f"tm1py_subset_{position}"
        subset_literal = ti_string(subset_name)
        title_element = getattr(selection, "selected", None)

        if subset is not None and subset.name and title_element is None:
            subset_literal = ti_string(subset.name)
        elif title_element is not None or (subset is not None and subset.elements and not subset.expression):
            elements = [title_element] if title_element is not None else subset.elements
            lines.append(f"SubsetCreate({dimension_literal}, {subset_literal}, 1);")
            lines += [
                f"SubsetElementInsert({dimension_literal}, {subset_literal}, {ti_string(element)}, {index});"
                for index, element in enumerate(elements, start=1)
            ]
        else:
            if subset is not None and subset.expression:
                mdx = subset.expression
            elif selection is None:
                mdx = f"{{[{_mdx_name(_normalize(dimension))}].[{_mdx_name(_normalize(dimension))}].DEFAULTMEMBER}}"
            else:
                mdx = f"{{TM1SUBSETALL([{_mdx_name(_normalize(dimension))}].[{_mdx_name(_normalize(dimension))}])}}"
            lines += ti_string_assignment("sMdx", mdx)
            lines.append(f"SubsetCreateByMDX({subset_literal}, sMdx, {dimension_literal}, 1);")
        lines.append(f"ViewSubsetAssign({cube}, {view}, {dimension_literal}, {subset_literal});")
    return lines


def _lean_export_data(profile: CubeProfile, layout: CsvLayout, spec: ExportSpec, file_name: str) -> str:
    file_literal = ti_string(file_name)
    lines = []

    # the character set applies only to the procedure it is set in (v11), and a file written in the prolog is
    # overwritten by the data procedure (v12), so both are set up on the first record
    first_record = [f"  SetOutputCharacterSet({file_literal},'TM1CS_UTF8');"]
    if layout.header:
        first_record.append("  " + _lean_header_ti(file_name, layout))
    lines += ["IF (nRecord = 0);", *first_record, "  nRecord = 1;", "ENDIF;"]

    if spec.top or spec.skip:
        skip = spec.skip or 0
        lines.append("nCell = nCell + 1;")
        if spec.top:
            lines += [f"IF (nCell > {spec.top + skip});", "  ProcessBreak;", "ENDIF;"]
        if skip:
            lines += [f"IF (nCell <= {skip});", "  ItemSkip;", "ENDIF;"]

    if profile.is_v12:
        # v12 occasionally produces tiny numbers (e.g. 4.94066e-324) instead of 0
        lines += [f"IF (ISUNDEFINEDCELLVALUE(NVALUE,{ti_string(profile.cube_name)}) = 1);", "  SVALUE = '0';", "ENDIF;"]

    aliases = {_normalize(dimension): alias for dimension, alias in (spec.aliases or {}).items()}
    written = spec.written_variables
    for variable in written:
        alias = aliases.get(_normalize(variable.dimension))
        if alias is None:
            continue
        # a blank alias falls back to the element name
        lines += [
            f"sAlias = ElementAttrS({ti_string(variable.dimension)}, {ti_string(variable.hierarchy_name)}, "
            f"{variable.name}, {ti_string(alias)});",
            "IF (sAlias @<> '');",
            f"  {variable.name} = sAlias;",
            "ENDIF;",
        ]

    if layout.quote_character:
        for variable in written:
            # alias values are not checked up front, so aliased dimensions are always escaped
            if profile.has_quotes(variable.dimension) or _normalize(variable.dimension) in aliases:
                lines.append(_escape_quotes_ti(variable.name, layout.quote_character))
        if profile.string_measures or profile.is_attribute_cube:
            lines += [
                "IF (VALUE_IS_STRING = 1);",
                _escape_quotes_ti("SVALUE", layout.quote_character, indent="  "),
                "ENDIF;",
            ]

    output = ",".join([variable.name for variable in written] + ["SVALUE"])
    lines.append(f"TextOutput({file_literal},{output});")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------------------------------------------- #
# load
# ---------------------------------------------------------------------------------------------------------------- #


def build_load_process(profile: CubeProfile, layout: CsvLayout, spec: LoadSpec, lean: bool = False) -> Process:
    """Build an unbound process that loads ``spec.file_name`` into the profile's cube.

    The file holds one column per cube dimension, in the cube's natural order, followed by the value.
    """
    file_name = ti_file_name(spec.file_name, profile.is_v12)
    process = Process(
        name=spec.process_name,
        datasource_type="ASCII",
        datasource_ascii_header_records=1 if (lean and layout.header) else 0,
        datasource_data_source_name_for_server=file_name,
        datasource_data_source_name_for_client=file_name,
        datasource_ascii_delimiter_char=layout.delimiter,
        datasource_ascii_decimal_separator=".",
        datasource_ascii_thousand_separator="",
        datasource_ascii_quote_character=layout.quote_character,
    )

    dimension_variables = [f"v{n}" for n in range(1, len(profile.dimensions) + 1)]
    for variable in dimension_variables:
        process.add_variable(name=variable, variable_type="String")

    if lean:
        numeric_value = _lean_load_is_numeric(profile, spec)
        process.add_variable(name="vValue", variable_type="Numeric" if numeric_value else "String")
        process.prolog_procedure = _lean_load_prolog(profile, spec)
        process.data_procedure = _lean_load_data(profile, spec, dimension_variables, numeric_value)
    else:
        process.add_variable(name="vValue", variable_type="String")
        process.prolog_procedure = _legacy_load_prolog(profile, spec)
        process.data_procedure = _legacy_load_data(profile, spec, dimension_variables)
    return process


def _legacy_load_prolog(profile: CubeProfile, spec: LoadSpec) -> str:
    prolog = f"""
        SetInputCharacterSet('TM1CS_UTF8');
        {enable_sandbox_ti(spec.sandbox_name, profile.sandboxing_disabled)}
        """
    if spec.clear_view:
        prolog = prolog + f"\rViewZeroOut('{profile.cube_name}', '{spec.clear_view}');\r"
    return prolog


def _numeric_put_function(profile: CubeProfile, spec: LoadSpec) -> str:
    if profile.is_attribute_cube:
        return "CellPutN"
    return "CellIncrementN" if spec.increment else "CellPutN"


def _element_type_branching(
    profile: CubeProfile, spec: LoadSpec, dimension_variables: List[str], string: Callable[[str], str]
) -> str:
    """The load statement that checks element types on every row (legacy, and lean for attribute cubes / spread)."""
    cube_name = string(profile.cube_name)
    cube_measure = string(profile.measure_dimension)
    variable_cube_measure = dimension_variables[-1]
    comma_sep_var_elements = ",".join(dimension_variables)
    numeric_function_str = _numeric_put_function(profile, spec)

    # Define input statement depending on measure element's type: numeric or string
    # For non-existing-element attempt to write to trigger error
    # For consolidated elements spread if allowed else let fail.
    measure_type_equal = f"ElementType({cube_measure}, '', {variable_cube_measure}) @= "
    n_write_types = ["'N'", "'AN'", "'C'", "''"]
    numeric_write_condition = "% \n".join([measure_type_equal + possible_type for possible_type in n_write_types])

    any_c_element_in_write = "% \n".join(
        [f"ElementType({string(dim)}, '', {ele}) @= 'C'" for dim, ele in zip(profile.dimensions, dimension_variables)]
    )

    numeric_write_statement_with_spread = f"""
            nValue = StringToNumber(vValue);
            IF({any_c_element_in_write});
                CellPutProportionalSpread(nValue,{cube_name},{comma_sep_var_elements});
            ELSE;
                {numeric_function_str}(nValue,{cube_name},{comma_sep_var_elements});
            ENDIF;
            """

    numeric_write_statement_without_spread = f"""
            nValue = StringToNumber(vValue);
            {numeric_function_str}(nValue,{cube_name},{comma_sep_var_elements});
            """

    string_write_condition = f"""
            ElementType({cube_measure}, '', {variable_cube_measure}) @= 'S' %{_SPACE}
            ElementType({cube_measure}, '', {variable_cube_measure}) @= 'AS' %{_SPACE}
            ElementType({cube_measure}, '', {variable_cube_measure}) @= 'AA'
            """

    string_write_statement = f"""
            sValue = vValue;
            CellPutS(sValue,{cube_name},{comma_sep_var_elements});{_SPACE}
            """

    return f"""
        If({numeric_write_condition});
            {numeric_write_statement_with_spread if spec.allow_spread else numeric_write_statement_without_spread}
        ElseIf({string_write_condition});
            {string_write_statement}
        EndIf;"""


def _legacy_load_data(profile: CubeProfile, spec: LoadSpec, dimension_variables: List[str]) -> str:
    comma_sep_var_elements = ",".join(dimension_variables)
    if spec.skip_non_updateable:
        cell_is_updateable_pre = f"If( CellIsUpdateable('{profile.cube_name}',{comma_sep_var_elements}) = 1 );"
        cell_is_updateable_post = "\rElse;\r" "   ItemSkip;\r" "EndIf;\r"
    else:
        cell_is_updateable_pre = ""
        cell_is_updateable_post = ""
    input_statement = _element_type_branching(profile, spec, dimension_variables, _legacy_string)
    return cell_is_updateable_pre + input_statement + cell_is_updateable_post


def _lean_load_is_numeric(profile: CubeProfile, spec: LoadSpec) -> bool:
    """Whether the lean load can read the value as a number and write it with a single numeric put."""
    return not (profile.string_measures or profile.is_attribute_cube or spec.allow_spread)


def _lean_load_prolog(profile: CubeProfile, spec: LoadSpec) -> str:
    lines = ["SetInputCharacterSet('TM1CS_UTF8');"]
    sandbox = enable_sandbox_ti(spec.sandbox_name, profile.sandboxing_disabled)
    if sandbox:
        lines.append(sandbox)
    if spec.clear_view:
        lines.append(f"ViewZeroOut({ti_string(profile.cube_name)}, {ti_string(spec.clear_view)});")
    return "\n".join(lines) + "\n"


def _lean_load_data(profile: CubeProfile, spec: LoadSpec, dimension_variables: List[str], numeric_value: bool) -> str:
    cube = ti_string(profile.cube_name)
    coordinates = ",".join(dimension_variables)
    measure_variable = dimension_variables[-1]
    put_n = _numeric_put_function(profile, spec)

    if numeric_value:
        statement = f"{put_n}(vValue,{cube},{coordinates});"
    elif profile.is_attribute_cube or spec.allow_spread:
        statement = _element_type_branching(profile, spec, dimension_variables, ti_string).strip("\n")
    else:
        statement = "\n".join(
            [
                f"IF ({_string_measure_condition(profile, measure_variable)});",
                f"  CellPutS(vValue,{cube},{coordinates});",
                "ELSE;",
                f"  {put_n}(StringToNumber(vValue),{cube},{coordinates});",
                "ENDIF;",
            ]
        )

    if spec.skip_non_updateable:
        statement = "\n".join(
            [
                f"IF (CellIsUpdateable({cube},{coordinates}) = 1);",
                *("  " + line for line in statement.split("\n")),
                "ELSE;",
                "  ItemSkip;",
                "ENDIF;",
            ]
        )
    return statement + "\n"


def _string_measure_condition(profile: CubeProfile, measure_variable: str) -> str:
    measures = sorted(profile.string_measures)
    if len(measures) > MAX_STRING_MEASURES_BY_NAME:
        return f"ElementType({ti_string(profile.measure_dimension)}, '', {measure_variable}) @= 'S'"
    # TI string comparison ignores case
    return " % ".join(f"{measure_variable} @= {ti_string(measure)}" for measure in measures)
