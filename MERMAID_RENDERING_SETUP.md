# Mermaid Rendering Setup

## Goal

Enable Mermaid-based process flow diagrams to be rendered as images and embedded into the exported PDD.

## How the pipeline works

1. backend builds structured process steps
2. backend generates Mermaid flowchart text
3. Mermaid CLI renders that flowchart into a PNG image
4. DOCX/PDF export embeds that PNG into the `Process Flow Diagram` section

If Mermaid CLI is not available:

- export still works
- Mermaid source text is placed into the template context
- the diagram image will not be embedded

## Required runtime dependency

The backend machine must have Mermaid CLI available as:

```text
mmdc
```

in the system `PATH`.

## Typical installation

Mermaid CLI is usually installed through Node.js:

```bash
npm install -g @mermaid-js/mermaid-cli
```

After installation, verify:

```bash
mmdc --version
```

## Backend behavior

The backend checks for Mermaid CLI using:

```text
shutil.which("mmdc")
```

If found:

- Mermaid diagram is rendered into PNG
- PNG path is used for `pdd.process_flow.diagram_image`

If not found:

- no image is rendered
- `pdd.process_flow.mermaid_source` remains available as fallback

## Export template fields

Available process-flow fields:

```text
pdd.process_flow.mermaid_source
pdd.process_flow.diagram_path
pdd.process_flow.diagram_image
pdd.process_flow.rendered
```

## Recommended template usage

```text
5. Process Flow Diagram
{% if pdd.process_flow.diagram_image %}
{{ pdd.process_flow.diagram_image }}
{% else %}
Mermaid Source:
{{ pdd.process_flow.mermaid_source }}
{% endif %}
```

## Recommendation

For team or server deployment:

- install Mermaid CLI once on the backend machine
- keep DOCX/PDF export template configured to use `pdd.process_flow.diagram_image`

That gives the best export behavior with minimal runtime branching.
