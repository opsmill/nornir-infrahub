# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is `nornir-infrahub`, a Nornir plugin that integrates with Infrahub by OpsMill. The project provides:

- **Inventory Plugin**: `InfrahubInventory` - fetches inventory data from Infrahub and maps it to Nornir hosts and groups
- **Task Plugins**: Artifact management tasks for generating, regenerating, and retrieving artifacts from Infrahub

## Development Commands

### Testing

```bash
pytest                                              # Run all tests
pytest tests/unit/test_inventory.py                 # Run specific test file
pytest tests/unit/test_inventory.py::test_function  # Run single test function
```

### Linting and Code Quality

```bash
invoke lint              # Run all linters (yaml, ruff, pylint, mypy)
invoke lint-ruff         # Run ruff linter only
invoke lint-pylint       # Run pylint only
invoke lint-mypy         # Run mypy type checking only
invoke lint-yaml         # Run yamllint only
invoke format            # Auto-format code with ruff
```

### Documentation

```bash
invoke docs-install      # Install npm dependencies for docs
invoke docs-serve        # Start dev server at http://localhost:3000
invoke docs-build        # Build documentation website (requires npm)
invoke generate-docs     # Generate plugin documentation from docstrings
```

## Architecture

### Core Components

1. **Inventory Plugin** (`nornir_infrahub/plugins/inventory/infrahub.py`):
   - `InfrahubInventory` class: Main inventory plugin that connects to Infrahub API
   - Fetches nodes from Infrahub and maps them to Nornir hosts using configurable schema mappings
   - Supports group creation based on Infrahub node attributes/relations
   - Uses `infrahub-sdk` for API communication

2. **Task Plugins** (`nornir_infrahub/plugins/tasks/artifact.py`):
   - `get_artifact()`: Retrieve artifact content from Infrahub storage
   - `generate_artifacts()`: Trigger artifact generation for all targets in definition
   - `regenerate_host_artifact()`: Regenerate artifact for specific host

### Key Dependencies

- `infrahub-sdk`: Primary SDK for Infrahub API interactions
- `nornir`: Core automation framework
- `pydantic`: Data validation and settings management
- `ruamel.yaml`: YAML processing for configuration files

### Configuration Pattern

The inventory plugin expects:

- `host_node`: Dict defining which Infrahub node kind maps to Nornir hosts
- `schema_mappings`: List mapping Nornir host properties to Infrahub node attributes/relations
- `group_mappings`: List of Infrahub attributes to create Nornir groups from
- Optional YAML files for defaults and static groups

### Plugin Registration

Plugins are automatically registered via Poetry entry points:

```toml
[tool.poetry.plugins."nornir.plugins.inventory"]
"InfrahubInventory" = "nornir_infrahub.plugins.inventory.infrahub:InfrahubInventory"
```

## Important Notes

- All task plugins expect the host to have an `InfrahubNode` in `host.data["InfrahubNode"]`
- The inventory plugin automatically includes `member_of_groups` relation for group membership
- Artifact tasks use direct HTTP calls with `httpx` rather than the SDK for some operations
- Error handling uses RuntimeError for mapping resolution failures (TODO items exist for improvement)

## Documentation Guidelines

### Documentation Writing Guidelines

**Applies to:** All MDX files (`**/*.mdx`)

**Role:** Expert Technical Writer and MDX Generator with:

- Deep understanding of Infrahub and its capabilities
- Expertise in network automation and infrastructure management
- Proficiency in writing structured MDX documents
- Awareness of developer ergonomics

**Documentation Purpose:**

- Guide users through installing, configuring, and using Infrahub in real-world workflows
- Explain concepts and system architecture clearly, including new paradigms introduced by Infrahub
- Support troubleshooting and advanced use cases with actionable, well-organized content
- Enable adoption by offering approachable examples and hands-on guides that lower the learning curve

**Structure:** Follows [Diataxis framework](https://diataxis.fr/)

- **Tutorials** (learning-oriented)
- **How-to guides** (task-oriented)
- **Explanation** (understanding-oriented)
- **Reference** (information-oriented)

**Tone and Style:**

- Professional but approachable: Avoid jargon unless well defined. Use plain language with technical precision
- Concise and direct: Prefer short, active sentences. Reduce fluff
- Informative over promotional: Focus on explaining how and why, not on marketing
- Consistent and structured: Follow a predictable pattern across sections and documents

**For Guides:**

- Use conditional imperatives: "If you want X, do Y. To achieve W, do Z."
- Focus on practical tasks and problems, not the tools themselves
- Address the user directly using imperative verbs: "Configure...", "Create...", "Deploy..."
- Maintain focus on the specific goal without digressing into explanations
- Use clear titles that state exactly what the guide shows how to accomplish

**For Topics:**

- Use a more discursive, reflective tone that invites understanding
- Include context, background, and rationale behind design decisions
- Make connections between concepts and to users' existing knowledge
- Present alternative perspectives and approaches where appropriate
- Use illustrative analogies and examples to deepen understanding

**Terminology and Naming:**

- Always define new terms when first used. Use callouts or glossary links if possible
- Prefer domain-relevant language that reflects the user's perspective (e.g., playbooks, branches, schemas, commits)
- Be consistent: follow naming conventions established by Infrahub's data model and UI

**Reference Files:**

- Vale styles: `.vale/styles/Infrahub/`
- Spelling exceptions: `.vale/styles/spelling-exceptions.txt`
- Markdown linting: `.markdownlint.yaml`

### Document Structure Patterns (Following Diataxis)

**How-to Guides Structure (Task-oriented, practical steps):**

```markdown
- Title and Metadata
    - Title should clearly state what problem is being solved (YAML frontmatter)
    - Begin with "How to..." to signal the guide's purpose
    - Optional: Imports for components (e.g., Tabs, TabItem, CodeBlock, VideoPlayer)
- Introduction
    - Brief statement of the specific problem or goal this guide addresses
    - Context or real-world use case that frames the guide
    - Clearly indicate what the user will achieve by following this guide
    - Optional: Links to related topics or more detailed documentation
- Prerequisites / Assumptions
    - What the user should have or know before starting
    - Environment setup or requirements
    - What prior knowledge is assumed
- Step-by-Step Instructions
    - Step 1: [Action/Goal]
        - Clear, actionable instructions focused on the task
        - Code snippets (YAML, GraphQL, shell commands, etc.)
        - Screenshots or images for visual guidance
        - Tabs for alternative methods (e.g., Web UI, GraphQL, Shell/cURL)
        - Notes, tips, or warnings as callouts
    - Step 2: [Action/Goal]
        - Repeat structure as above for each step
    - Step N: [Action/Goal]
        - Continue as needed
- Validation / Verification
    - How to check that the solution worked as expected
    - Example outputs or screenshots
    - Potential failure points and how to address them
- Advanced Usage / Variations
    - Optional: Alternative approaches for different circumstances
    - Optional: How to adapt the solution for related problems
    - Optional: Ways to extend or optimize the solution
- Related Resources
    - Links to related guides, reference materials, or explanation topics
    - Optional: Embedded videos or labs for further learning
```

**Topics Structure (Understanding-oriented, theoretical knowledge):**

```markdown
- Title and Metadata
    - Title should clearly indicate the topic being explained (YAML frontmatter)
    - Consider using "About..." or "Understanding..." in the title
    - Optional: Imports for components (e.g., Tabs, TabItem, CodeBlock, VideoPlayer)
- Introduction
    - Brief overview of what this explanation covers
    - Why this topic matters in the context of Infrahub
    - Questions this explanation will answer
- Main Content Sections
    - Concepts & Definitions
        - Clear explanations of key terms and concepts
        - How these concepts fit into the broader system
    - Background & Context
        - Historical context or evolution of the concept/feature
        - Design decisions and rationale behind implementations
        - Technical constraints or considerations
    - Architecture & Design (if applicable)
        - Diagrams, images, or explanations of structure
        - How components interact or relate to each other
    - Mental Models
        - Analogies and comparisons to help understanding
        - Different ways to think about the topic
    - Connection to Other Concepts
        - How this topic relates to other parts of Infrahub
        - Integration points and relationships
    - Alternative Approaches
        - Different perspectives or methodologies
        - Pros and cons of different approaches
- Further Reading
    - Links to related topics, guides, or reference materials
    - External resources for deeper understanding
```

### Quality and Clarity Checklist

**General Documentation:**

- Content is accurate and reflects the latest version of Infrahub
- Instructions are clear, with step-by-step guidance where needed
- Markdown formatting is correct and compliant with Infrahub's style
- Spelling and grammar are checked

**For Guides:**

- The guide addresses a specific, practical problem or task
- The title clearly indicates what will be accomplished
- Steps follow a logical sequence that maintains flow
- Each step focuses on actions, not explanations
- The guide omits unnecessary details that don't serve the goal
- Validation steps help users confirm their success
- The guide addresses real-world complexity rather than oversimplified scenarios

**For Topics:**

- The explanation is bounded to a specific topic area
- Content provides genuine understanding, not just facts
- Background and context are included to deepen understanding
- Connections are made to related concepts and the bigger picture
- Different perspectives or approaches are acknowledged where relevant
- The content remains focused on explanation without drifting into tutorial or reference material
- The explanation answers "why" questions, not just "what" or "how"

## Other items

- Always run markdownlint when .md or .mdx files change
- Always run vale when .md or .mdx files change
