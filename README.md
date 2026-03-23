# paychecks

Validates paycheck pdfs and compares with W2s at end of year.

Sample project to develop using [spec-kit](https://github.com/github/spec-kit).

## Setup

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git

specify init . --ai claude

# Check installed tools
specify check
```

In `claude`:

```text
# Create your project's governing principles and development guidelines that will guide all subsequent development.
/speckit.constitution Create principles focused on code quality, testing standards, user experience consistency, and performance requirements

# Describe what you want to build. Focus on the what and why, not the tech stack.
/speckit.specify Build an application that can help me organize my photos in separate photo albums. Albums are grouped by date and can be re-organized by dragging and dropping on the main page. Albums are never in other nested albums. Within each album, photos are previewed in a tile-like interface.

# Clarify underspecified areas (recommended before /speckit.plan).
/speckit.clarify	

# Provide your tech stack and architecture choices.
/speckit.plan The application uses Vite with minimal number of libraries. Use vanilla HTML, CSS, and JavaScript as much as possible. Images are not uploaded anywhere and metadata is stored in a local SQLite database.

# Create an actionable task list from your implementation plan.
/speckit.tasks

# Cross-artifact consistency & coverage analysis (run after /speckit.tasks, before /speckit.implement).
/speckit.analyze	

# Use /speckit.implement to execute all tasks and build your feature according to the plan.
/speckit.implement

# Generate custom quality checklists that validate requirements completeness, clarity, and consistency (like "unit tests for English")
/speckit.checklist
```