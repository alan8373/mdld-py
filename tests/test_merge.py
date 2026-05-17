"""Merge tests, transliterated from tests/merge.tests.js."""
from __future__ import annotations
from textwrap import dedent

from mdld_parse import merge, parse
from .conftest import has_quad, quad_key


def test_primary_subjects_single_document():
    md = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Employee {=my:emp456 .my:Employee}
        [Alice] {my:name}""")
    result = merge([md])
    assert len(result['primarySubjects']) == 1
    assert result['primarySubjects'][0] == 'tag:hr@example.com,2026:emp456'


def test_primary_subjects_multiple_documents():
    doc1 = dedent("""\
        [ex] <http://example.org/>
        # Doc1 {=ex:doc1}
        [Value] {label}""")
    doc2 = dedent("""\
        [ex] <http://example.org/>
        # Doc2 {=ex:doc2}
        [Value] {label}""")
    result = merge([doc1, doc2])
    assert len(result['primarySubjects']) == 2
    assert result['primarySubjects'][0] == 'http://example.org/doc1'
    assert result['primarySubjects'][1] == 'http://example.org/doc2'


def test_primary_subjects_doc_with_no_primary():
    doc1 = dedent("""\
        [ex] <http://example.org/>
        # Doc1 {=ex:doc1}
        [Value] {label}""")
    doc2 = '[Value] {label}'
    result = merge([doc1, doc2])
    assert len(result['primarySubjects']) == 1
    assert result['primarySubjects'][0] == 'http://example.org/doc1'


def test_primary_subjects_parse_result_input():
    doc1 = parse({'text': dedent("""\
        [ex] <http://example.org/>
        # Doc1 {=ex:doc1}
        [Value] {label}""")})
    doc2 = parse({'text': dedent("""\
        [ex] <http://example.org/>
        # Doc2 {=ex:doc2}
        [Value] {label}""")})
    result = merge([doc1, doc2])
    assert len(result['primarySubjects']) == 2
    assert result['primarySubjects'][0] == 'http://example.org/doc1'
    assert result['primarySubjects'][1] == 'http://example.org/doc2'


def test_single_document_equivalence_to_parse():
    md = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Employee {=my:emp456 .my:Employee}
        [Alice] {my:name}""")
    result = merge([md])
    assert len(result['quads']) == len(parse(md)['quads'])
    assert len(result['remove']) == 0
    assert len(result['origin']['documents']) == 1


def test_single_document_with_appended_diff():
    md = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Employee {=my:emp456 .my:Employee}
        [Software Engineer] {my:jobTitle}

        ---

        # Employee {=my:emp456}
        [Software Engineer] {-my:jobTitle}
        [Senior Software Engineer] {my:jobTitle}""")
    result = merge([md])
    assert len(result['quads']) == 2
    assert has_quad(result['quads'], 'tag:hr@example.com,2026:emp456',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'tag:hr@example.com,2026:Employee')
    assert has_quad(result['quads'], 'tag:hr@example.com,2026:emp456',
                    'tag:hr@example.com,2026:jobTitle', 'Senior Software Engineer')
    assert len(result['remove']) == 0


def test_single_document_external_retract():
    md = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Employee {=my:emp456}
        [Software Engineer] {-my:jobTitle}
        [Senior Software Engineer] {my:jobTitle}""")
    result = merge([md])
    assert len(result['quads']) == 1
    assert len(result['remove']) == 1
    assert has_quad(result['remove'], 'tag:hr@example.com,2026:emp456',
                    'tag:hr@example.com,2026:jobTitle', 'Software Engineer')


def test_two_documents_inter_document_cancel():
    doc1 = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Employee {=my:emp456 .my:Employee}
        [Software Engineer] {my:jobTitle}""")
    doc2 = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Employee {=my:emp456}
        [Software Engineer] {-my:jobTitle}
        [Senior Software Engineer] {my:jobTitle}""")
    result = merge([doc1, doc2])
    assert len(result['quads']) == 2
    assert has_quad(result['quads'], 'tag:hr@example.com,2026:emp456',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'tag:hr@example.com,2026:Employee')
    assert has_quad(result['quads'], 'tag:hr@example.com,2026:emp456',
                    'tag:hr@example.com,2026:jobTitle', 'Senior Software Engineer')
    assert len(result['remove']) == 0
    assert len(result['origin']['documents']) == 2


def test_type_migration_single_annotation():
    md = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Project {=my:proj .my:ActiveProject}
        # Project {=my:proj -.my:ActiveProject .my:ArchivedProject}""")
    result = merge([md])
    assert len(result['quads']) == 1
    assert has_quad(result['quads'], 'tag:hr@example.com,2026:proj',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'tag:hr@example.com,2026:ArchivedProject')
    assert not has_quad(result['quads'], 'tag:hr@example.com,2026:proj',
                        'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                        'tag:hr@example.com,2026:ActiveProject')


def test_parseresult_passthrough_no_reparse():
    md = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Employee {=my:emp456 .my:Employee}
        [Alice] {my:name}""")
    parsed = parse({'text': md})
    result = merge([parsed, md], {'context': {'my': 'tag:hr@example.com,2026:'}})
    assert len(result['origin']['documents']) == 2
    assert result['origin']['documents'][0]['input'] == 'ParseResult'
    assert result['origin']['documents'][1]['input'] == 'string'


def test_hard_invariant_quads_remove_disjoint():
    md = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Employee {=my:emp456}
        [Software Engineer] {my:jobTitle}
        [Software Engineer] {-my:jobTitle}
        [Senior Software Engineer] {my:jobTitle}""")
    result = merge([md])
    quad_keys = {quad_key(q) for q in result['quads']}
    for r in result['remove']:
        assert quad_key(r) not in quad_keys


def test_four_document_replay_chain():
    genesis = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Employee {=my:emp456 .my:Employee}""")
    promotion = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Employee {=my:emp456}
        [Junior Software Engineer] {my:jobTitle}""")
    reorg = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Employee {=my:emp456}
        [Junior Software Engineer] {-my:jobTitle}
        [Software Engineer] {my:jobTitle}""")
    salary = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Employee {=my:emp456}
        [Software Engineer] {-my:jobTitle}
        [Senior Software Engineer] {my:jobTitle}""")
    result = merge([genesis, promotion, reorg, salary])
    assert len(result['quads']) == 2
    assert has_quad(result['quads'], 'tag:hr@example.com,2026:emp456',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'tag:hr@example.com,2026:Employee')
    assert has_quad(result['quads'], 'tag:hr@example.com,2026:emp456',
                    'tag:hr@example.com,2026:jobTitle', 'Senior Software Engineer')
    assert len(result['origin']['documents']) == 4


def test_mixed_polarity_in_single_annotation():
    md = dedent("""\
        [my] <tag:hr@example.com,2026:>
        # Doc {=my:doc -.my:Draft .my:Published -my:version}
        [2.0] {my:version}""")
    result = merge([md])
    assert len(result['quads']) == 2
    assert has_quad(result['quads'], 'tag:hr@example.com,2026:doc',
                    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
                    'tag:hr@example.com,2026:Published')
    assert has_quad(result['quads'], 'tag:hr@example.com,2026:doc',
                    'tag:hr@example.com,2026:version', '2.0')


def test_statements_merging():
    doc1 = dedent("""\
        [ex] <http://example.org/>

        ## Statement 1 {=ex:stmt1 .rdf:Statement}
        **Alice** {+ex:alice ?rdf:subject} *knows* {+ex:knows ?rdf:predicate} **Bob** {+ex:bob ?rdf:object}

        **Alice** {=ex:alice} knows **Bob** {?ex:knows +ex:bob}""")
    doc2 = dedent("""\
        [ex] <http://example.org/>

        ## Statement 2 {=ex:stmt2 .rdf:Statement}
        **Charlie** {+ex:charlie ?rdf:subject} *works with* {+ex:works-with ?rdf:predicate} **David** {+ex:david ?rdf:object}

        **Charlie** {=ex:charlie} works with **David** {?ex:works-with +ex:david}""")
    result = merge([doc1, doc2])
    assert len(result['statements']) == 2
    alice_knows_bob = next((s for s in result['statements']
                            if s.subject.value == 'http://example.org/alice'
                            and s.predicate.value == 'http://example.org/knows'
                            and s.object.value == 'http://example.org/bob'), None)
    charlie_works_david = next((s for s in result['statements']
                                 if s.subject.value == 'http://example.org/charlie'
                                 and s.predicate.value == 'http://example.org/works-with'
                                 and s.object.value == 'http://example.org/david'), None)
    assert alice_knows_bob is not None
    assert charlie_works_david is not None


def test_context_accumulation_across_documents():
    doc1 = dedent("""\
        [ex1] <http://example.org/1/>
        # Person {=ex1:alice}
        [Alice] {ex1:name}""")
    doc2 = dedent("""\
        [ex2] <http://example.org/2/>
        # Person {=ex2:bob}
        [Bob] {ex2:name}""")
    result = merge([doc1, doc2])
    assert result['context']['ex1'] == 'http://example.org/1/'
    assert result['context']['ex2'] == 'http://example.org/2/'
    assert len(result['quads']) == 2
