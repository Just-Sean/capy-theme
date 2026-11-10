# Design Tokens format schema (test data)

`format-2025.10.json` is the official JSON Schema of the W3C Design Tokens
Community Group's Design Tokens Format Module 2025.10, downloaded unchanged from
<https://www.designtokens.org/schemas/2025.10/format.json>. The tests check that
capy-theme's design-tokens download validates against it. It's only used by the
tests and isn't part of the package.

Copyright © the W3C Design Tokens Community Group contributors, licensed under
the [W3C Software and Document License](https://www.w3.org/Consortium/Legal/2015/copyright-software-and-document).
Source: <https://github.com/design-tokens/community-group>.

To update it to a newer format version:

```bash
curl -sSfL -o tests/artifacts/dtcg/format-2025.10.json https://www.designtokens.org/schemas/2025.10/format.json
```
