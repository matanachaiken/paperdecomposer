import anthropic
import PyPDF2
import sys
import os
import json
import re

# --- Schema for each section ---
SCHEMAS = {
    "OVERVIEW":             ["title", "authors", "year", "summary"],
    "METHODOLOGY":          ["approach", "techniques", "frameworks"],
    "CORE ASSUMPTIONS":     ["assumptions", "requirements"],
    "DATA & INPUTS":        ["datasets", "source", "size", "preprocessing"],
    "EXPERIMENTAL DESIGN":  ["structure", "baselines", "comparisons", "validation"],
    "EVALUATION METRICS":   ["metrics", "rationale", "findings"],
    "LIMITATIONS":          ["acknowledged", "additional_weaknesses"],
    "KEY TAKEAWAYS":        ["takeaways", "practical_applications"]
}

# --- Section headers commonly found in academic papers ---
SECTION_MARKERS = {
    "OVERVIEW":             ["abstract"],
    "METHODOLOGY":          ["methodology", "methods", "approach", "proposed method"],
    "CORE ASSUMPTIONS":     ["assumptions", "background", "preliminaries"],
    "DATA & INPUTS":        ["data", "dataset", "corpus", "inputs"],
    "EXPERIMENTAL DESIGN":  ["experiment", "experimental setup", "evaluation setup"],
    "EVALUATION METRICS":   ["results", "evaluation", "metrics", "performance"],
    "LIMITATIONS":          ["limitation", "future work", "discussion"],
    "KEY TAKEAWAYS":        ["conclusion", "summary", "takeaway"]
}

def extract_text(pdf_path):
    """Extract text from PDF, returning full text and detected sections."""
    full_text = ""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        print(f"Reading {len(reader.pages)} pages...")
        for i, page in enumerate(reader.pages):
            t = page.extract_text()
            if t:
                full_text += f"\n--- Page {i+1} ---\n{t}"
    return full_text

def chunk_by_sections(full_text):
    """Split paper text into sections based on detected headers."""
    lines = full_text.split("\n")
    sections = {}
    current_section = "OVERVIEW"
    current_text = []

    for line in lines:
        line_lower = line.lower().strip()
        matched = False

        for section, markers in SECTION_MARKERS.items():
            for marker in markers:
                # Match lines that start with or are mostly a section header
                if re.match(rf"^({marker})[\s\:\.\d]*$", line_lower):
                    # Save previous section
                    if current_text:
                        sections[current_section] = sections.get(current_section, "") + "\n".join(current_text)
                    current_section = section
                    current_text = []
                    matched = True
                    break
            if matched:
                break

        if not matched:
            current_text.append(line)

    # Save last section
    if current_text:
        sections[current_section] = sections.get(current_section, "") + "\n".join(current_text)

    return sections

def validate_json(data, required_keys):
    """Validate that JSON response contains all required keys."""
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise ValueError(f"Missing keys: {missing}")
    return True

def decompose(full_text, api_key):
    client = anthropic.Anthropic(api_key=api_key)

    # Chunk paper into sections
    print("Chunking paper into sections...")
    sections_text = chunk_by_sections(full_text)
    detected = list(sections_text.keys())
    print(f"Detected sections: {detected}")

    prompts = {
        "OVERVIEW": "Extract: title, authors, year, and a 3-sentence plain-English summary of what this paper is about and why it matters.",
        "METHODOLOGY": "Describe: the approach taken, techniques/models used, and frameworks employed.",
        "CORE ASSUMPTIONS": "List: the key assumptions the authors make, and what must be true for their approach to work.",
        "DATA & INPUTS": "Describe: datasets used, their source, size, and any preprocessing steps.",
        "EXPERIMENTAL DESIGN": "Describe: how experiments were structured, baselines used, comparisons made, and how results were validated.",
        "EVALUATION METRICS": "List: the metrics used, why they were chosen, and what the key findings were.",
        "LIMITATIONS": "List: limitations the authors acknowledge and additional weaknesses not mentioned.",
        "KEY TAKEAWAYS": "List: the 3-5 most important takeaways and practical applications of this research."
    }

    results = {}

    for section, instruction in prompts.items():
        print(f"Extracting {section}...")

        # Use section-specific chunk if detected, else fall back to full text
        chunk = sections_text.get(section, full_text)[:8000]
        schema = SCHEMAS[section]

        prompt = f"""You are an expert research analyst. Analyze this section of an academic paper.

{instruction}

CRITICAL: You must respond ONLY with a valid JSON object. No preamble, no explanation, no markdown.
The JSON must contain exactly these keys: {schema}
Each value should be a string or list of strings.

Example format:
{{
  "{schema[0]}": "your answer here",
  "{schema[1]}": ["point 1", "point 2"]
}}

Paper section:
---
{chunk}
---"""

        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = message.content[0].text.strip()
        raw = re.sub(r"```json|```", "", raw).strip()

        # JSON validation
        try:
            parsed = json.loads(raw)
            validate_json(parsed, schema)
            results[section] = parsed
            print(f"  ✓ Valid JSON")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"  ⚠ Validation failed ({e}), storing raw text")
            results[section] = {"raw": raw}

    return results

def format_output(results):
    """Format validated JSON results into readable text."""
    output = ""
    for section, data in results.items():
        output += f"\n\n{'='*60}\n{section}\n{'='*60}\n"
        if "raw" in data:
            output += data["raw"]
        else:
            for key, value in data.items():
                output += f"\n{key.upper().replace('_', ' ')}:\n"
                if isinstance(value, list):
                    for item in value:
                        output += f"  • {item}\n"
                else:
                    output += f"  {value}\n"
    return output

if __name__ == "__main__":
    api_key = "sk-ant-paste-your-key-here"

    pdf_path = sys.argv[1] if len(sys.argv) > 1 else input("Path to PDF: ").strip()

    if not os.path.exists(pdf_path):
        print("File not found.")
        sys.exit(1)

    full_text = extract_text(pdf_path)
    print("Decomposing paper...")
    results = decompose(full_text, api_key)
    output = format_output(results)

    output_path = pdf_path.replace(".pdf", "_breakdown.txt")
    with open(output_path, "w") as f:
        f.write(output)

    print(f"\nDone! Saved to: {output_path}")
    print(output)
