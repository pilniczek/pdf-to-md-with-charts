"""
pdf_to_md.py — Convert PDF to Markdown, with diagrams/charts converted by Claude.

Usage:
    python pdf_to_md.py input.pdf output.md

Requirements:
    pip install -r requirements.txt

Environment:
    ANTHROPIC_API_KEY  — your Anthropic API key
"""

import sys
import os
import re
import base64
import tempfile
import shutil
import anthropic
import pymupdf4llm


DIAGRAM_PROMPT = """\
Analyze this image and decide if it is a structured informational visual:
a diagram, flowchart, architecture schema, chart, graph, or any figure
that conveys structured information worth representing in text.

NOT included: photos, decorative images, backgrounds, logos, icons, or
any image whose information cannot be meaningfully expressed as text.

If YES → reply starting with the word CONVERT (on its own line), then
provide a full, accurate Markdown representation of all the information
in the image. Use headings, bullet lists, tables, or nested lists as
appropriate. Do not add commentary — only the Markdown content.

If NO → reply with just the word: SKIP
"""


def image_to_base64(path: str) -> tuple[str, str]:
    """Return (base64_data, media_type) for a PNG/JPEG image file."""
    ext = os.path.splitext(path)[1].lower()
    media_type = "image/png" if ext == ".png" else "image/jpeg"
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode(), media_type


def get_image_dimensions(path: str) -> tuple[int, int]:
    """Return (width, height) in pixels using pymupdf."""
    try:
        import pymupdf
        pix = pymupdf.Pixmap(path)
        return pix.width, pix.height
    except Exception:
        return 0, 0


def classify_and_convert(client: anthropic.Anthropic, image_path: str) -> str | None:
    """
    Send the image to Claude.
    Returns Markdown string if it's a diagram, or None if it should be omitted.
    """
    b64, media_type = image_to_base64(image_path)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": b64},
                },
                {"type": "text", "text": DIAGRAM_PROMPT},
            ],
        }],
    )

    text = response.content[0].text.strip()
    if text.upper().startswith("CONVERT"):
        return text[len("CONVERT"):].lstrip("\n").strip()
    return None


def process(pdf_path: str, output_md: str) -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # --- Step 1: Convert PDF → Markdown, saving picture regions as PNGs ---
    img_dir = tempfile.mkdtemp(prefix="pdf_imgs_")
    try:
        print(f"[1/3] Converting PDF to Markdown (extracting images) ...")
        md = pymupdf4llm.to_markdown(
            pdf_path,
            write_images=True,
            image_path=img_dir,
            image_format="png",
        )

        # --- Step 2: Find all image references in the markdown ---
        img_pattern = re.compile(r'!\[.*?\]\(([^)]+\.png)\)')
        matches = list(img_pattern.finditer(md))
        print(f"[2/3] Found {len(matches)} picture region(s). Classifying with Claude ...")

        replacements: list[tuple[re.Match, str]] = []

        for i, m in enumerate(matches):
            img_ref_path = m.group(1)

            # Resolve path — may be relative to cwd or img_dir
            img_abs_path = img_ref_path
            if not os.path.isabs(img_ref_path):
                candidate = os.path.join(os.getcwd(), img_ref_path)
                if not os.path.exists(candidate):
                    candidate = os.path.join(img_dir, os.path.basename(img_ref_path))
                img_abs_path = candidate

            w, h = get_image_dimensions(img_abs_path)
            size_label = f"{w}x{h}"
            print(f"  [{i+1}/{len(matches)}] {os.path.basename(img_abs_path)} ({size_label}) ... ", end="", flush=True)

            if not os.path.exists(img_abs_path):
                print("file not found — keeping as omitted")
                replacements.append((m, f"\n==> picture [{size_label}] intentionally omitted <==\n"))
                continue

            result = classify_and_convert(client, img_abs_path)
            if result:
                print("diagram → converting to Markdown")
                replacements.append((m, f"\n{result}\n"))
            else:
                print("not a diagram → omitting")
                replacements.append((m, f"\n==> picture [{size_label}] intentionally omitted <==\n"))

        # --- Step 3: Apply replacements (back-to-front to preserve offsets) ---
        print("[3/3] Writing output ...")
        result_md = md
        for match, replacement in reversed(replacements):
            result_md = result_md[: match.start()] + replacement + result_md[match.end():]

        with open(output_md, "w", encoding="utf-8") as f:
            f.write(result_md)

        print(f"\nDone! Saved to: {output_md}")

    finally:
        shutil.rmtree(img_dir, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    process(sys.argv[1], sys.argv[2])
