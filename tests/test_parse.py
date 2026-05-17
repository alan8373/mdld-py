"""Parser tests, transliterated from tests/parse.tests.js."""
from __future__ import annotations
from textwrap import dedent

from mdld_parse import parse, generate
from .conftest import find_quad, has_quad


# ---------------------------------------------------------------------------
# §17 Primary Subject
# ---------------------------------------------------------------------------

def test_primary_subject_first_declaration():
    md = dedent("""\
        [ex] <http://example.org/>

        # Document {=ex:doc .ex:Article label}
        [Alice] {ex:author}""")
    assert parse(md)['primary_subject'] == 'http://example.org/doc'


def test_primary_subject_null_when_no_subject():
    assert parse('[Alice] {label}')['primary_subject'] is None


def test_primary_subject_fragment_does_not_become_primary():
    md = dedent("""\
        [ex] <http://example.org/>

        # Document {=ex:doc}
        {=#summary}
        [Content] {label}""")
    assert parse(md)['primary_subject'] == 'http://example.org/doc'


def test_primary_subject_reset_does_not_clear():
    md = dedent("""\
        [ex] <http://example.org/>

        # First {=ex:first}
        [Value] {label}

        # Reset {=}

        # Second {=ex:second}
        [Value] {label}""")
    assert parse(md)['primary_subject'] == 'http://example.org/first'


def test_primary_subject_first_non_fragment_wins():
    md = dedent("""\
        [ex] <http://example.org/>

        {=#summary}
        [Content] {label}

        # Document {=ex:doc}
        [Alice] {ex:author}""")
    assert parse(md)['primary_subject'] == 'http://example.org/doc'


def test_primary_subject_round_trip_with_generate():
    md = dedent("""\
        [ex] <http://example.org/>

        # Document {=ex:doc .ex:Article label}
        [Alice] {ex:author}""")
    parsed = parse(md)
    gen = generate(quads=parsed['quads'], context={'ex': 'http://example.org/'},
                   primary_subject=parsed['primary_subject'])
    re_parsed = parse({'text': gen['text'], 'context': gen['context']})
    assert parsed['primary_subject'] == re_parsed['primary_subject']


# ---------------------------------------------------------------------------
# §6 Subject Declaration
# ---------------------------------------------------------------------------

def test_subject_declaration_sets_context():
    md = dedent("""\
        [ex] <http://example.org/>
        # Title {=ex:doc}

        [value] {label}""")
    quads = parse(md)['quads']
    assert has_quad(quads, 'http://example.org/doc',
                    'http://www.w3.org/2000/01/rdf-schema#label', 'value')


def test_subject_reset_with_equals():
    md = dedent("""\
        [ex] <http://example.org/>
        # First {=ex:first}

        [value1] {label}

        # Reset {=}

        [value2] {label}""")
    quads = parse(md)['quads']
    assert len(quads) == 1
    assert has_quad(quads, 'http://example.org/first',
                    'http://www.w3.org/2000/01/rdf-schema#label', 'value1')


# ---------------------------------------------------------------------------
# §7 Type Declaration
# ---------------------------------------------------------------------------

def test_type_declaration_emits_rdf_type():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Doc {=ex:doc .schema:Article}""")
    quads = parse(md)['quads']
    assert has_quad(quads, 'http://example.org/doc',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'http://schema.org/Article')


def test_multiple_types_on_same_subject():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Doc {=ex:doc .schema:Article .schema:CreativeWork}""")
    quads = parse(md)['quads']
    assert len(quads) == 2
    assert has_quad(quads, 'http://example.org/doc',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'http://schema.org/Article')
    assert has_quad(quads, 'http://example.org/doc',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'http://schema.org/CreativeWork')


# ---------------------------------------------------------------------------
# §8.1 Predicate forms
# ---------------------------------------------------------------------------

def test_literal_property():
    md = dedent("""\
        [ex] <http://example.org/>

        # Doc {=ex:doc}

        [Alice] {label}""")
    q = find_quad(parse(md)['quads'], 'http://example.org/doc',
                  'http://www.w3.org/2000/01/rdf-schema#label', 'Alice')
    assert q is not None
    assert q.object.term_type == 'Literal'


def test_multiple_literal_properties():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Doc {=ex:doc}

        [Alice] {label schema:author}""")
    quads = parse(md)['quads']
    assert len(quads) == 2
    assert has_quad(quads, 'http://example.org/doc',
                    'http://www.w3.org/2000/01/rdf-schema#label', 'Alice')
    assert has_quad(quads, 'http://example.org/doc',
                    'http://schema.org/author', 'Alice')


def test_object_property():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Doc {=ex:doc}

        [Alice] {=ex:alice ?schema:author}""")
    q = find_quad(parse(md)['quads'], 'http://example.org/doc',
                  'http://schema.org/author', 'http://example.org/alice')
    assert q is not None
    assert q.object.term_type == 'NamedNode'


def test_object_property_with_resource_declaration():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Doc {=ex:doc}

        [Alice] {=ex:alice ?schema:author .schema:Person}""")
    quads = parse(md)['quads']
    assert len(quads) == 2
    assert has_quad(quads, 'http://example.org/doc',
                    'http://schema.org/author', 'http://example.org/alice')
    assert has_quad(quads, 'http://example.org/alice',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'http://schema.org/Person')


def test_object_property_without_object_emits_nothing():
    md = dedent("""\
        [ex] <http://example.org/>

        # Doc {=ex:doc}

        [Alice] {?author}""")
    assert len(parse(md)['quads']) == 0


def test_reverse_object_property():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Doc {=ex:doc}

        [Parent] {=ex:parent !schema:hasPart}""")
    q = find_quad(parse(md)['quads'], 'http://example.org/parent',
                  'http://schema.org/hasPart', 'http://example.org/doc')
    assert q is not None


# ---------------------------------------------------------------------------
# §9 Datatypes & language tags
# ---------------------------------------------------------------------------

def test_datatype_annotation():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Doc {=ex:doc}

        [42] {schema:count ^^xsd:integer}""")
    q = find_quad(parse(md)['quads'], 'http://example.org/doc',
                  'http://schema.org/count', '42')
    assert q.object.datatype.value == 'http://www.w3.org/2001/XMLSchema#integer'


def test_language_tag():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Doc {=ex:doc}

        [Hello] {schema:greeting @en}""")
    q = find_quad(parse(md)['quads'], 'http://example.org/doc',
                  'http://schema.org/greeting', 'Hello')
    assert q.object.language == 'en'


def test_multiple_datatypes():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Doc {=ex:doc}

        [2024-01-01] {schema:date ^^xsd:date}
        [19.99] {schema:price ^^xsd:decimal}""")
    quads = parse(md)['quads']
    date_q = find_quad(quads, 'http://example.org/doc',
                       'http://schema.org/date', '2024-01-01')
    price_q = find_quad(quads, 'http://example.org/doc',
                        'http://schema.org/price', '19.99')
    assert date_q.object.datatype.value == 'http://www.w3.org/2001/XMLSchema#date'
    assert price_q.object.datatype.value == 'http://www.w3.org/2001/XMLSchema#decimal'


def test_empty_literal_still_emits():
    md = dedent("""\
        [ex] <http://example.org/>

        # Doc {=ex:doc}

        [] {label}""")
    quads = parse(md)['quads']
    assert len(quads) == 1
    assert quads[0].object.value == ''


def test_literal_with_special_characters():
    md = dedent("""\
        [ex] <http://example.org/>

        # Doc {=ex:doc}

        [Hello "world"! @#$%] {label}""")
    q = find_quad(parse(md)['quads'], 'http://example.org/doc',
                  'http://www.w3.org/2000/01/rdf-schema#label',
                  'Hello "world"! @#$%')
    assert q is not None


def test_multiple_predicates_on_same_carrier():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Doc {=ex:doc}

        [Value] {label schema:description schema:author}""")
    quads = parse(md)['quads']
    assert len(quads) == 3


def test_mixed_datatype_and_language_prioritizes_language():
    md = dedent("""\
        [ex] <http://example.org/>

        # Doc {=ex:doc}

        [Hello] {label @en ^^xsd:string}""")
    q = find_quad(parse(md)['quads'], 'http://example.org/doc',
                  'http://www.w3.org/2000/01/rdf-schema#label', 'Hello')
    assert q.object.language == 'en'
    assert q.object.datatype.value == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#langString'


# ---------------------------------------------------------------------------
# Prefix declarations & folding
# ---------------------------------------------------------------------------

def test_prefix_declarations():
    md = dedent("""\
        [ex] <http://example.org/>

        # Doc {=ex:doc}

        [value] {ex:property}""")
    quads = parse(md)['quads']
    assert has_quad(quads, 'http://example.org/doc',
                    'http://example.org/property', 'value')


def test_prefix_folding_basic():
    md = dedent("""\
        [base] <https://example.com/>
        [doc] <base:document/>
        [auth] <base:author/>

        # Test {=doc:test1 auth:created}""")
    result = parse(md)
    assert result['context']['doc'] == 'https://example.com/document/'
    assert result['context']['auth'] == 'https://example.com/author/'
    assert has_quad(result['quads'], 'https://example.com/document/test1',
                    'https://example.com/author/created', 'Test')


def test_prefix_folding_forward_reference_is_literal():
    md = dedent("""\
        [j] <my:journal:>
        [my] <tag:mymail@domain.com,2026:>

        # Test {=j:test}""")
    ctx = parse(md)['context']
    assert ctx['j'] == 'my:journal:'
    assert ctx['my'] == 'tag:mymail@domain.com,2026:'


def test_prefix_folding_circular_safety():
    md = dedent("""\
        [a] <b:test>
        [b] <a:test>

        # Test {=a:test}""")
    ctx = parse(md)['context']
    assert ctx['a'] == 'b:test'
    assert ctx['b'] == 'b:testtest'


def test_prefix_folding_redeclaration_overrides():
    md = dedent("""\
        [my] <tag:mymail@domain.com,2026:>
        [my] <https://example.com/new/>
        [j] <my:journal:>

        # Test {=j:test}""")
    ctx = parse(md)['context']
    assert ctx['my'] == 'https://example.com/new/'
    assert ctx['j'] == 'https://example.com/new/journal:'


def test_prefix_folding_multilevel():
    md = dedent("""\
        [org] <https://org.example.com/>
        [person] <org:person/>
        [emp] <person:employee/>
        [dev] <emp:developer/>

        # Test {=dev:john emp:worksFor}""")
    result = parse(md)
    assert result['context']['org'] == 'https://org.example.com/'
    assert result['context']['person'] == 'https://org.example.com/person/'
    assert result['context']['emp'] == 'https://org.example.com/person/employee/'
    assert result['context']['dev'] == 'https://org.example.com/person/employee/developer/'
    assert has_quad(result['quads'],
                    'https://org.example.com/person/employee/developer/john',
                    'https://org.example.com/person/employee/worksFor', 'Test')


# ---------------------------------------------------------------------------
# Inline carriers
# ---------------------------------------------------------------------------

def test_multiple_inline_carriers():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Doc {=ex:doc}

        Author is [Alice] {label} and [Bob] {schema:contributor}""")
    quads = parse(md)['quads']
    assert len(quads) == 2
    assert has_quad(quads, 'http://example.org/doc',
                    'http://www.w3.org/2000/01/rdf-schema#label', 'Alice')
    assert has_quad(quads, 'http://example.org/doc',
                    'http://schema.org/contributor', 'Bob')


def test_all_inline_carrier_variants():
    md = dedent("""\
        [ex] <http://example.org/>
        [@vocab] <http://example.org/>

        # Document {=ex:doc}

        [span] {spanName}
        *emphasis* {emphasisName}
        **strong** {strongName}
        _underline_ {underlineName}
        __double_underline__ {doubleUnderlineName}
        `code` {codeName}
        [link](http://example.com) {linkName}""")
    quads = parse(md)['quads']
    assert len(quads) == 7
    assert has_quad(quads, 'http://example.org/doc', 'http://example.org/spanName', 'span')
    assert has_quad(quads, 'http://example.org/doc', 'http://example.org/emphasisName', 'emphasis')
    assert has_quad(quads, 'http://example.org/doc', 'http://example.org/strongName', 'strong')
    assert has_quad(quads, 'http://example.org/doc', 'http://example.org/underlineName', 'underline')
    assert has_quad(quads, 'http://example.org/doc', 'http://example.org/doubleUnderlineName', 'double_underline')
    assert has_quad(quads, 'http://example.org/doc', 'http://example.org/codeName', 'code')
    assert has_quad(quads, 'http://example.com', 'http://example.org/linkName', 'link')


def test_multiple_inline_carriers_on_same_line():
    md = dedent("""\
        [ex] <http://example.org/>
        [@vocab] <http://example.org/>

        # Document {=ex:doc}

        [span] {spanName} *emphasis* {emphasisName} **strong** {strongName}""")
    quads = parse(md)['quads']
    assert len(quads) == 3


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_annotation_emits_nothing():
    md = dedent("""\
        [ex] <http://example.org/>

        # Doc {=ex:doc}

        [value] {}""")
    assert len(parse(md)['quads']) == 0


def test_annotation_without_subject_emits_nothing():
    assert len(parse('[value] {label}')['quads']) == 0


def test_plain_paragraph_without_annotation_ignored():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Doc {=ex:doc}

        This is plain text.

        [value] {label}""")
    assert len(parse(md)['quads']) == 1


def test_malformed_annotation_ignored():
    md = dedent("""\
        [ex] <http://example.org/>

        # Doc {=ex:doc}

        [Value] {name incomplete""")
    assert len(parse(md)['quads']) == 0


def test_nested_brackets_do_not_crash():
    md = dedent("""\
        [ex] <http://example.org/>

        # Doc {=ex:doc}

        [Value [nested]] {label}""")
    quads = parse(md)['quads']
    assert len(quads) == 1
    q = find_quad(quads, 'http://example.org/doc',
                  'http://www.w3.org/2000/01/rdf-schema#label', 'Value [nested]')
    assert q is not None


# ---------------------------------------------------------------------------
# Soft IRI / fragment
# ---------------------------------------------------------------------------

def test_soft_iri_with_object_predicate():
    md = dedent("""\
        [schema] <http://schema.org/>
        [wd] <http://www.wikidata.org/entity/>

        # Apollo 11 {=wd:Q43653}

        Part of the [Apollo Program] {+wd:Q495307 ?schema:partOf}
        and launched on a [Saturn V] {+wd:Q193237 ?schema:vehicle}.""")
    quads = parse(md)['quads']
    assert len(quads) == 2
    assert has_quad(quads, 'http://www.wikidata.org/entity/Q43653',
                    'http://schema.org/partOf', 'http://www.wikidata.org/entity/Q495307')
    assert has_quad(quads, 'http://www.wikidata.org/entity/Q43653',
                    'http://schema.org/vehicle', 'http://www.wikidata.org/entity/Q193237')


def test_soft_iri_with_reverse_predicate():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Document {=ex:doc}

        [Parent] {+ex:parent !schema:hasPart}""")
    quads = parse(md)['quads']
    assert len(quads) == 1
    assert has_quad(quads, 'http://example.org/parent',
                    'http://schema.org/hasPart', 'http://example.org/doc')


def test_soft_iri_with_type():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Project {=ex:project}

        [Team Lead] {+ex:alice ?schema:teamLead .schema:Person}""")
    quads = parse(md)['quads']
    assert len(quads) == 2
    assert has_quad(quads, 'http://example.org/project',
                    'http://schema.org/teamLead', 'http://example.org/alice')
    assert has_quad(quads, 'http://example.org/alice',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'http://schema.org/Person')


def test_fragment_uses_current_subject_iri_base():
    md = dedent("""\
        [ex] <http://example.org/>

        # Document {=ex:document}

        {=#summary}
        [This is the summary] {label}""")
    quads = parse(md)['quads']
    assert has_quad(quads, 'http://example.org/document#summary',
                    'http://www.w3.org/2000/01/rdf-schema#label',
                    'This is the summary')


def test_fragment_replaces_existing_fragment():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Document {=ex:document}

        ## Section {=#section1}
        [Section content] {schema:headline}

        ## Subsection {=#subsection}
        [Content here] {label}""")
    quads = parse(md)['quads']
    assert has_quad(quads, 'http://example.org/document#section1',
                    'http://schema.org/headline', 'Section content')
    assert has_quad(quads, 'http://example.org/document#subsection',
                    'http://www.w3.org/2000/01/rdf-schema#label', 'Content here')


def test_fragment_without_current_subject_emits_nothing():
    md = dedent("""\
        [ex] <http://example.org/>

        {=#summary}
        [Content] {label}""")
    assert len(parse(md)['quads']) == 0


# ---------------------------------------------------------------------------
# Code blocks
# ---------------------------------------------------------------------------

def test_fenced_code_block_skips_annotations():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Document {=ex:doc}

        ```mdld
        [This should be ignored] {label schema:description}
        ```

        [This should be processed] {label}""")
    quads = parse(md)['quads']
    assert len(quads) == 1
    assert has_quad(quads, 'http://example.org/doc',
                    'http://www.w3.org/2000/01/rdf-schema#label',
                    'This should be processed')


def test_fenced_code_block_processes_fence_annotation():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Document {=ex:doc}

        ```mdld {label schema:description}
        [This should be ignored] {label schema:description}
        ```

        [This should be processed] {label}""")
    quads = parse(md)['quads']
    assert len(quads) == 3


def test_tilde_fenced_block():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Document {=ex:doc}

        ~~~mdld
        [This should be ignored] {label schema:description}
        ~~~

        [This should be processed] {label}""")
    quads = parse(md)['quads']
    assert len(quads) == 1
    assert has_quad(quads, 'http://example.org/doc',
                    'http://www.w3.org/2000/01/rdf-schema#label',
                    'This should be processed')


def test_exact_fence_length_matching():
    md = dedent("""\
        [ex] <http://example.org/>

        # Document {=ex:doc}

        ~~~~~~mdld
        [Content with ~~~~ inside] {label}
        More content
        ~~~~~~

        [Processed] {label}""")
    quads = parse(md)['quads']
    assert len(quads) == 1
    assert has_quad(quads, 'http://example.org/doc',
                    'http://www.w3.org/2000/01/rdf-schema#label', 'Processed')


def test_mixed_fence_types_backticks_in_tilde():
    md = ('[ex] <http://example.org/>\n\n'
          '# Document {=ex:doc}\n\n'
          '~~~mdld\n[Content] {label}\n```\nStill content [inside] {label}\n~~~\n\n'
          '[Processed] {label}')
    quads = parse(md)['quads']
    assert len(quads) == 1


def test_fence_detection_ignores_indentation():
    md = ('[ex] <http://example.org/>\n\n'
          '# Document {=ex:doc}\n\n'
          '    ~~~mdld\n    [Indented content] {label}\n    ~~~\n\n'
          '[Processed] {label}')
    quads = parse(md)['quads']
    assert len(quads) == 1
    assert has_quad(quads, 'http://example.org/doc',
                    'http://www.w3.org/2000/01/rdf-schema#label', 'Processed')


def test_code_block_with_attribute():
    md = ('[ex] <http://example.org/>\n[schema] <http://schema.org/>\n\n'
          '# Document {=ex:doc}\n\n'
          '```javascript {ex:attribute}\n'
          '[Code example] {label schema:description}\n'
          'console.log("hello");\n'
          '```')
    quads = parse(md)['quads']
    assert len(quads) == 1
    assert has_quad(quads, 'http://example.org/doc', 'http://example.org/attribute',
                    '[Code example] {label schema:description}\nconsole.log("hello");')


# ---------------------------------------------------------------------------
# Datatype validation
# ---------------------------------------------------------------------------

def test_boolean_datatype():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Doc {=ex:doc}

        [true] {schema:active ^^xsd:boolean}
        [false] {schema:completed ^^xsd:boolean}""")
    quads = parse(md)['quads']
    true_q  = find_quad(quads, 'http://example.org/doc', 'http://schema.org/active', 'true')
    false_q = find_quad(quads, 'http://example.org/doc', 'http://schema.org/completed', 'false')
    assert true_q.object.datatype.value == 'http://www.w3.org/2001/XMLSchema#boolean'
    assert false_q.object.datatype.value == 'http://www.w3.org/2001/XMLSchema#boolean'


# ---------------------------------------------------------------------------
# Subject chaining
# ---------------------------------------------------------------------------

def test_subject_chaining_with_standalone_declarations():
    md = dedent("""\
        [ex] <http://example.org/>

        ## Main Event {=ex:main-event .schema:Event}
        Title: [Main Title] {schema:title}
        Description: [Main description] {schema:description}

        {=ex:sub-event-1 .schema:Event}
        Sub title: [Sub Title 1] {schema:title}
        Sub description: [Sub description 1] {schema:description}

        {=ex:sub-event-2 .schema:Event}
        Sub title: [Sub Title 2] {schema:title}
        Sub description: [Sub description 2] {schema:description}

        Back to main: [Back to main] {schema:description}""")
    quads = parse(md, {'context': {'schema': 'http://schema.org/'}})['quads']
    assert has_quad(quads, 'http://example.org/main-event',
                    'http://schema.org/title', 'Main Title')
    assert has_quad(quads, 'http://example.org/sub-event-1',
                    'http://schema.org/title', 'Sub Title 1')
    assert has_quad(quads, 'http://example.org/sub-event-2',
                    'http://schema.org/title', 'Sub Title 2')
    assert has_quad(quads, 'http://example.org/sub-event-2',
                    'http://schema.org/description', 'Back to main')
    assert has_quad(quads, 'http://example.org/main-event',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'http://schema.org/Event')


def test_subject_reset_with_standalone_equals():
    md = dedent("""\
        [ex] <http://example.org/>

        ## First {=ex:first}
        Title: [First Title] {schema:title}
        Description: [First description] {schema:description}

        {=}
        Title: [No subject title] {schema:title}
        Description: [No subject description] {schema:description}""")
    quads = parse(md, {'context': {'schema': 'http://schema.org/'}})['quads']
    assert has_quad(quads, 'http://example.org/first',
                    'http://schema.org/title', 'First Title')
    assert not has_quad(quads, 'http://example.org/first',
                        'http://schema.org/title', 'No subject title')
    assert len(quads) == 2


# ---------------------------------------------------------------------------
# Soft fragment
# ---------------------------------------------------------------------------

def test_soft_fragment_with_object_predicate():
    md = dedent("""\
        # Document {=ex:doc}

        [Section] {+#section1 label ?schema:hasPart}""")
    quads = parse(md, {'context': {'ex': 'http://example.org/',
                                   'schema': 'http://schema.org/'}})['quads']
    assert len(quads) == 2
    assert has_quad(quads, 'http://example.org/doc#section1',
                    'http://www.w3.org/2000/01/rdf-schema#label', 'Section')
    assert has_quad(quads, 'http://example.org/doc',
                    'http://schema.org/hasPart', 'http://example.org/doc#section1')


def test_soft_fragment_with_reverse_predicate():
    md = dedent("""\
        # Document {=ex:doc}

        [Parent] {+#parent !schema:hasPart}""")
    quads = parse(md, {'context': {'ex': 'http://example.org/',
                                   'schema': 'http://schema.org/'}})['quads']
    assert len(quads) == 1
    assert has_quad(quads, 'http://example.org/doc#parent',
                    'http://schema.org/hasPart', 'http://example.org/doc')


def test_soft_fragment_with_type():
    md = dedent("""\
        # Document {=ex:doc}

        [Chapter] {+#chapter1 .schema:Section label}""")
    quads = parse(md, {'context': {'ex': 'http://example.org/',
                                   'schema': 'http://schema.org/'}})['quads']
    assert len(quads) == 2
    assert has_quad(quads, 'http://example.org/doc#chapter1',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'http://schema.org/Section')
    assert has_quad(quads, 'http://example.org/doc#chapter1',
                    'http://www.w3.org/2000/01/rdf-schema#label', 'Chapter')


def test_soft_fragment_does_not_persist():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Doc {=ex:doc}

        [First] {+#frag1 ?schema:p}
        [Second] {?schema:p}""")
    quads = parse(md)['quads']
    assert len(quads) == 1
    assert has_quad(quads, 'http://example.org/doc',
                    'http://schema.org/p', 'http://example.org/doc#frag1')


def test_soft_iri_does_not_persist():
    md = dedent("""\
        [ex] <http://example.org/>
        [schema] <http://schema.org/>

        # Doc {=ex:doc}

        [First] {+ex:object1 ?schema:p}
        [Second] {?schema:p}""")
    quads = parse(md)['quads']
    assert len(quads) == 1
    assert has_quad(quads, 'http://example.org/doc',
                    'http://schema.org/p', 'http://example.org/object1')


# ---------------------------------------------------------------------------
# Angle-bracket URLs
# ---------------------------------------------------------------------------

def test_angle_bracket_url_soft_subject():
    md = dedent("""\
        [ex] <http://example.org/>
        [@vocab] <http://example.org/>

        # Document {=ex:doc}

        <https://nasa.gov> {.Organization} <https://arxiv.org/abs/2301.07041> {?cites .Paper}
        <https://doi.org/10.1000/xyz123> {!hasVersion .Article}""")
    quads = parse(md)['quads']
    assert len(quads) == 5
    assert has_quad(quads, 'https://nasa.gov',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'http://example.org/Organization')
    assert has_quad(quads, 'https://arxiv.org/abs/2301.07041',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'http://example.org/Paper')
    assert has_quad(quads, 'https://doi.org/10.1000/xyz123',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'http://example.org/Article')
    assert has_quad(quads, 'http://example.org/doc',
                    'http://example.org/cites', 'https://arxiv.org/abs/2301.07041')
    assert has_quad(quads, 'https://doi.org/10.1000/xyz123',
                    'http://example.org/hasVersion', 'http://example.org/doc')


def test_bracketed_link_type_uses_url_as_subject():
    md = dedent("""\
        [ex] <http://example.org/>
        [@vocab] <http://example.org/>

        # Document {=ex:doc}

        [NASA](https://nasa.gov) {.Organization}""")
    quads = parse(md)['quads']
    assert len(quads) == 1
    assert has_quad(quads, 'https://nasa.gov',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'http://example.org/Organization')


def test_list_items_maintain_subject_context():
    md = dedent("""\
        [ex] <http://example.org/>

        # Container {=ex:container .Container}

        List items:

        - Item1 {+ex:item1 ?member}
        - Item2 {+ex:item2 ?member}
        - Item3 {+ex:item3 ?member}""")
    quads = parse(md)['quads']
    assert has_quad(quads, 'http://example.org/container',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'http://www.w3.org/2000/01/rdf-schema#Container')
    for i in (1, 2, 3):
        assert has_quad(quads, 'http://example.org/container',
                        'http://www.w3.org/2000/01/rdf-schema#member',
                        f'http://example.org/item{i}')


# ---------------------------------------------------------------------------
# Diff polarity
# ---------------------------------------------------------------------------

def test_intra_document_cancel():
    md = dedent("""\
        [my] <tag:hr@example.com,2026:>

        # Employee {=my:emp456 .my:Employee}
        [Software Engineer] {my:jobTitle}
        [Software Engineer] {-my:jobTitle}
        [Senior Software Engineer] {my:jobTitle}""")
    result = parse(md)
    assert len(result['quads']) == 2
    assert has_quad(result['quads'], 'tag:hr@example.com,2026:emp456',
                    'tag:hr@example.com,2026:jobTitle', 'Senior Software Engineer')
    assert len(result['remove']) == 0


def test_external_retract_populates_remove():
    md = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Employee {=my:emp456}
        [Software Engineer] {-my:jobTitle}
        [Senior Software Engineer] {my:jobTitle}""")
    result = parse(md)
    assert len(result['quads']) == 1
    assert len(result['remove']) == 1
    assert has_quad(result['remove'], 'tag:hr@example.com,2026:emp456',
                    'tag:hr@example.com,2026:jobTitle', 'Software Engineer')


def test_type_migration_single_annotation():
    md = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Project Alpha {=my:proj -.my:ActiveProject .my:ArchivedProject}""")
    result = parse(md)
    assert len(result['quads']) == 1
    assert len(result['remove']) == 1
    assert has_quad(result['quads'], 'tag:hr@example.com,2026:proj',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'tag:hr@example.com,2026:ArchivedProject')
    assert has_quad(result['remove'], 'tag:hr@example.com,2026:proj',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'tag:hr@example.com,2026:ActiveProject')


def test_type_migration_with_prior_assertion():
    md = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Project Alpha {=my:proj .my:ActiveProject}
        # Project Alpha {=my:proj -.my:ActiveProject .my:ArchivedProject}""")
    result = parse(md)
    assert len(result['quads']) == 1
    assert len(result['remove']) == 0


def test_object_triple_remove():
    md = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Team {=my:team789}
        [old member] {-?my:hasMember +my:emp123}""")
    result = parse(md)
    assert len(result['quads']) == 0
    assert len(result['remove']) == 1
    assert has_quad(result['remove'], 'tag:hr@example.com,2026:team789',
                    'tag:hr@example.com,2026:hasMember',
                    'tag:hr@example.com,2026:emp123')


def test_reverse_triple_remove():
    md = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Chapter {=my:ch1}
        [Book] {-!my:hasPart +my:book}""")
    result = parse(md)
    assert len(result['quads']) == 0
    assert len(result['remove']) == 1
    assert has_quad(result['remove'], 'tag:hr@example.com,2026:book',
                    'tag:hr@example.com,2026:hasPart',
                    'tag:hr@example.com,2026:ch1')


def test_block_carriers_all_types():
    md = dedent("""\
        [my] <tag:hr@example.com,2026:>
        {=my:doc}
        # Old Title {-label}
        # New Title {label}
        > old quote {-prov:value}
        > new quote {prov:value}""")
    result = parse(md)
    assert len(result['quads']) == 2
    assert has_quad(result['quads'], 'tag:hr@example.com,2026:doc',
                    'http://www.w3.org/2000/01/rdf-schema#label', 'New Title')
    assert has_quad(result['quads'], 'tag:hr@example.com,2026:doc',
                    'http://www.w3.org/ns/prov#value', 'new quote')
    assert len(result['remove']) == 2


def test_subject_context_unaffected_by_remove_token():
    md = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Employee {=my:emp456}
        [Engineer] {-my:jobTitle}
        [Alice] {my:name}""")
    result = parse(md)
    assert len(result['quads']) == 1
    assert has_quad(result['quads'], 'tag:hr@example.com,2026:emp456',
                    'tag:hr@example.com,2026:name', 'Alice')


def test_invalid_minus_equals_warning_not_error():
    md = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Doc {-=my:doc .my:Article}""")
    result = parse(md)
    assert len(result['quads']) == 1
    assert has_quad(result['quads'], 'tag:hr@example.com,2026:doc',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'tag:hr@example.com,2026:Article')


def test_hard_invariant_quads_remove_disjoint():
    md = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Test {=my:test}
        [value] {label}
        [value] {-label}
        [value2] {label}""")
    result = parse(md)
    quad_keys = {f'{q.subject.value}|{q.predicate.value}|{q.object.value}' for q in result['quads']}
    for r in result['remove']:
        key = f'{r.subject.value}|{r.predicate.value}|{r.object.value}'
        assert key not in quad_keys
    assert len(result['quads']) == 1
    assert len(result['remove']) == 0


def test_round_trip_safety_with_labels_and_datatypes():
    quads = [
        type('Q', (), {
            'subject':   type('T', (), {'value': 'http://example.org/org', 'term_type': 'NamedNode'})(),
            'predicate': type('T', (), {'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type', 'term_type': 'NamedNode'})(),
            'object':    type('T', (), {'value': 'http://www.w3.org/ns/prov#Organization', 'term_type': 'NamedNode'})(),
        })()
    ]
    # Use real DataFactory for a clean test
    from mdld_parse import DataFactory
    df = DataFactory
    quads = [
        df.quad(df.named_node('http://example.org/org'),
                df.named_node('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
                df.named_node('http://www.w3.org/ns/prov#Organization')),
        df.quad(df.named_node('http://example.org/org'),
                df.named_node('http://www.w3.org/2000/01/rdf-schema#label'),
                df.literal('ACME Inc.')),
        df.quad(df.named_node('http://example.org/person'),
                df.named_node('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
                df.named_node('http://www.w3.org/ns/prov#Person')),
        df.quad(df.named_node('http://example.org/person'),
                df.named_node('http://www.w3.org/2000/01/rdf-schema#label'),
                df.literal('Alice Smith')),
        df.quad(df.named_node('http://example.org/person'),
                df.named_node('http://www.w3.org/2000/01/rdf-schema#label'),
                df.literal('Alicia')),
        df.quad(df.named_node('http://example.org/person'),
                df.named_node('http://example.org/birthDate'),
                df.literal('1994-09-21', df.named_node('http://www.w3.org/2001/XMLSchema#date'))),
        df.quad(df.named_node('http://example.org/person'),
                df.named_node('http://example.org/salary'),
                df.literal('75000', df.named_node('http://www.w3.org/2001/XMLSchema#integer'))),
        df.quad(df.named_node('http://example.org/person'),
                df.named_node('http://example.org/rating'),
                df.literal('4.5', df.named_node('http://www.w3.org/2001/XMLSchema#decimal'))),
        df.quad(df.named_node('http://example.org/person'),
                df.named_node('http://example.org/isActive'),
                df.literal('true', df.named_node('http://www.w3.org/2001/XMLSchema#boolean'))),
        df.quad(df.named_node('http://example.org/person'),
                df.named_node('http://example.org/email'),
                df.literal('alice@example.com')),
        df.quad(df.named_node('http://example.org/person'),
                df.named_node('http://example.org/worksAt'),
                df.named_node('http://example.org/org')),
    ]
    gen = generate(quads=quads, context={'ex': 'http://example.org/'})
    result = parse({'text': gen['text'], 'context': gen['context']})
    out = result['quads']
    assert has_quad(out, 'http://example.org/person',
                    'http://www.w3.org/2000/01/rdf-schema#label', 'Alice Smith')
    assert has_quad(out, 'http://example.org/person',
                    'http://www.w3.org/2000/01/rdf-schema#label', 'Alicia')
    assert has_quad(out, 'http://example.org/person',
                    'http://example.org/birthDate', '1994-09-21')
    assert has_quad(out, 'http://example.org/person',
                    'http://example.org/salary', '75000')
    assert has_quad(out, 'http://example.org/person',
                    'http://example.org/rating', '4.5')
    assert has_quad(out, 'http://example.org/person',
                    'http://example.org/isActive', 'true')
    assert has_quad(out, 'http://example.org/person',
                    'http://example.org/email', 'alice@example.com')
    assert has_quad(out, 'http://example.org/person',
                    'http://example.org/worksAt', 'http://example.org/org')
    assert has_quad(out, 'http://example.org/org',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'http://www.w3.org/ns/prov#Organization')
    assert has_quad(out, 'http://example.org/person',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'http://www.w3.org/ns/prov#Person')
    assert len(out) == 11
