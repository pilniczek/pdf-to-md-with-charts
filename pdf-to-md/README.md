# pdf-to-md

Convert PDF files to clean Markdown — including automatic conversion of diagrams, charts, and schemas to Markdown text using Claude's vision.

## How it works

1. **[pymupdf4llm](https://github.com/pymupdf/RAG)** converts the PDF to Markdown, preserving headings, lists, tables, and bold text. Picture regions are rendered as PNG files.
2. Each picture is sent to **Claude** (`claude-sonnet-4-6`) for classification:
   - Diagrams, flowcharts, schemas, charts → converted to Markdown (headings, lists, tables)
   - Logos, decorative images, photos → replaced with `==> picture intentionally omitted <==`

## Setup

```bash
pip install -r requirements.txt
```

Set your Anthropic API key:

```bash
# Windows
set ANTHROPIC_API_KEY=sk-ant-...

# macOS / Linux
export ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

```bash
python pdf_to_md.py input.pdf output.md
```

## Output example

```
## Software development life cycle: Before and after agentic coding tools

### Traditional SDLC *(Weeks–Months per cycle)*

1. Requirements and planning *(Days–Weeks)*
2. System design *(Weeks)*
...

| Traditional            | Agentic                      |
|------------------------|------------------------------|
| Sequential handoffs    | Fluid agent flow             |
| Human codes everything | Human guides, agent executes |
...

==> picture intentionally omitted <==   ← logo, skipped
```

## Dependencies

| Package | Purpose |
|---|---|
| `pymupdf4llm` | PDF → Markdown conversion + image extraction |
| `anthropic` | Claude API for diagram classification |
