# Contributing to Cammina AI

First off, thank you for considering contributing to Cammina AI! It's people like you that make open source such a great community to learn, inspire, and create.

## How to Contribute

1. **Fork the Repository**: Start by forking the `cammina-ai` repository to your GitHub account.
2. **Clone Locally**: Clone your fork to your local machine.
3. **Create a Branch**: Create a new branch for your feature or bug fix (`git checkout -b feature/your-feature-name`).
4. **Commit Changes**: Make your changes and commit them with descriptive commit messages.
5. **Push**: Push your branch to your fork (`git push origin feature/your-feature-name`).
6. **Submit a Pull Request**: Open a pull request against the `main` branch of the original repository.

## Development Setup

To set up the development environment, follow the Quick Start instructions in the `README.md`. 
Make sure you use the `cammina` CLI to easily test your changes:

```bash
./cammina start
```

### Microservices
The project is divided into several microservices:
- `apps/web`: React TypeScript frontend.
- `services/orchestrator`: The main brain.
- `services/local_agent`: Executes commands securely.
- `services/llm_manager`: Routes LLM calls.
- `services/memory`: Handles ChromaDB and SQLite storage.

When working on a specific service, ensure you activate its respective virtual environment (`.venv` or `venv`) before adding dependencies or running tests.

## Pull Request Process

- Ensure your code follows the established code style (use `npm run format` for the frontend).
- Include clear comments where the logic is complex.
- Update the `README.md` if you are adding new environment variables or CLI commands.
- We will review your PR and merge it as soon as possible!

## Code Style Guidelines

- **Python**: Follow PEP 8 standards. Use type hints (`-> str`, `: dict`) wherever possible.
- **TypeScript**: Use strict typing. Avoid `any`. Use `Tailwind` and `shadcn/ui` for styling consistency.
- **General**: Keep functions atomic and modular.

Thank you for contributing!
