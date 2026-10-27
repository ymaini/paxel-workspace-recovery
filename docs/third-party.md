# Third-party code and licensing inventory

The MIT license applies to original Paxel Workspace code and documentation only.
Copyright holder: ymaini and contributors. The standard MIT grant/disclaimer text
is unchanged. This is a technical provenance review, not professional legal advice.

No complete original or modified YC Paxel installer, container source, report,
transcript, database, asset pack or upstream scoring engine is distributed.
Compatibility code operates on a developer's locally obtained installer. It uses
function/variable names and a minimal two-line control-flow anchor for matching;
the replacement scope branch, guards, staging and verification logic are maintained
here. Generated copies and diffs remain private outputs outside this repository.
No right to relicense or redistribute YC's complete installer is asserted.

Runtime dependency `zstandard` is installed from its package distribution, not
vendored. Development/test/audit dependencies are declared in pyproject.toml or
installed separately. Their own license terms remain applicable. No dependency
source is bundled into our wheel. Review dependency notices when redistributing a
self-contained application or container rather than this source package.

Official documents are linked as references; no third-party manuals or marketing
assets are copied. Actions use pinned upstream Git commits and are not vendored.
If a future adapter needs substantial upstream code, obtain and document its license
before including it; uncertain rights block release of that material.
