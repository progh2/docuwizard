# Third-party notices

DocuWizard depends on the following open-source packages (runtime):

| Package | License (typical) | Role |
|---------|-------------------|------|
| PySide6 | LGPL / commercial | Desktop GUI |
| platformdirs | MIT | OS data/config paths |
| pypdf | BSD-3-Clause | PDF text extraction |
| python-docx | MIT | DOCX parsing |
| openpyxl | MIT | Excel parsing |
| Pillow | HPND-like | Image open for OCR |
| pytesseract | Apache-2.0 | Python wrapper for Tesseract |

**External tools (not bundled):**

| Tool | License | Role |
|------|---------|------|
| [Ollama](https://ollama.com) | MIT | Local LLM / embeddings |
| [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) | Apache-2.0 | Image OCR engine |

When distributing a packaged build, include this file and each dependency's
license text as required by that license. PySide6 (Qt) is LGPL—either dynamically
link, provide object files for relinking, or obtain a commercial Qt license.

To regenerate a license inventory from the current environment:

```bash
pip install pip-licenses
pip-licenses --format=markdown --with-urls
```
