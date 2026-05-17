import re

DEFAULT_CONTEXT: dict[str, str] = {
    '@vocab': 'http://www.w3.org/2000/01/rdf-schema#',
    'rdf':   'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs':  'http://www.w3.org/2000/01/rdf-schema#',
    'xsd':   'http://www.w3.org/2001/XMLSchema#',
    'sh':    'http://www.w3.org/ns/shacl#',
    'prov':  'http://www.w3.org/ns/prov#',
}

URL_REGEX             = re.compile(r'^(https?|ftp|mailto|tag|nih|urn|uuid|did|web|ipfs|ipns|data|file|urn:uuid):')
FENCE_REGEX           = re.compile(r'^(`{3,}|~{3,})(.*)')
PREFIX_REGEX          = re.compile(r'^\[([^\]]+)\]\s*<([^>]+)>')
HEADING_REGEX         = re.compile(r'^(#{1,6})\s+(.+?)(?:\s*(\{[^}]+\}))?$')
UNORDERED_LIST_REGEX  = re.compile(r'^(\s*)([-*+]|\d+\.)\s+(.+?)(?:\s*(\{[^}]+\}))?\s*$')
BLOCKQUOTE_REGEX      = re.compile(r'^>\s+(.+?)(?:\s*(\{[^}]+\}))?$')
STANDALONE_SUBJECT_REGEX = re.compile(r'^\s*\{=(.*?)\}\s*$')

# Carrier patterns – checked in this order; double-backtick before single to avoid submatch
CARRIER_PATTERN_ARRAY = [
    ('EMPHASIS',        re.compile(r'[*_]+(.+?)[*_]+\s*\{([^}]+)\}')),
    ('CODE_SPAN_DOUBLE',re.compile(r'``(.+?)``\s*\{([^}]+)\}')),
    ('CODE_SPAN_SINGLE',re.compile(r'`(.+?)`\s*\{([^}]+)\}')),
]
