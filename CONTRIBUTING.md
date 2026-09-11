<!--
SPDX-FileCopyrightText: 2026 Oldemar Jesus Gonçalves <oldemar@techboystore.uk>

SPDX-License-Identifier: MIT
-->

# Contributing to MKV Subtitle Extractor & Gemini Subtitle Translator

Thank you for your interest in contributing! We welcome contributions from everyone.

## Code of Conduct

This project and everyone participating in it is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How to Contribute

### 1. Reporting Bugs
- Check existing [GitHub Issues](../../issues) before submitting a new one.
- Use the **Bug Report** template.
- Include OS version, Python version, FFmpeg version, and steps to reproduce (or sample SRT snippets).

### 2. Suggesting Enhancements
- Open a **Feature Request** issue describing the use case and proposed behavior.

### 3. Submitting Pull Requests
1. Fork the repository and create a new feature branch from `main`:
   ```bash
   git checkout -b feature/my-new-feature
   ```
2. Set up the development environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Make your changes adhering to PEP 8 standards and typing annotations.
4. Run automated tests to ensure nothing is broken:
   ```bash
   python3 -m unittest test_srt_and_extractor.py
   ```
5. Add tests for new functionality whenever applicable.
6. Commit your changes with a descriptive message and sign off your commits (DCO):
   ```bash
   git commit -s -m "feat: add support for ass subtitle format"
   ```
7. Push to your fork and submit a Pull Request against `main`.

## Developer Certificate of Origin (DCO)

To ensure legal compliance and transparency under open source standards, we require all contributors to agree to the Developer Certificate of Origin (DCO) version 1.1:

```
Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```

Simply include `-s` / `--signoff` in your `git commit` commands to append `Signed-off-by: Your Name <your.email@example.com>`.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
