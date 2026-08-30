"""The self-knowledge organ.

Every other organ in this body knows something about the outside world. None of
them knew anything about the body itself: the company that owns it, the person
answerable for it, or what it is supposed to be working towards. Those answers
were sitting in the repository's own documents the whole time — the company
record, the operating-core charter, the README, the synthesis — read by nobody.

This package reads them, and only them:

- :mod:`aureon.identity.reader` walks a repository root and assembles a
  :class:`~aureon.identity.schemas.SelfKnowledge` from real documents.
- :mod:`aureon.identity.schemas` models it so that a value without a source
  cannot exist: every field is either a
  :class:`~aureon.identity.schemas.SourcedFact` carrying the file it came from,
  or ``None`` with a blocker saying where it was looked for.

No connector, no network, no memory of a previous run, and not one company
detail written into the source. She answers from the documents in front of her,
or she says she does not know.
"""

from aureon.identity.reader import read_identity
from aureon.identity.schemas import Identity, SelfKnowledge, SourcedFact

__all__ = ["Identity", "SelfKnowledge", "SourcedFact", "read_identity"]
