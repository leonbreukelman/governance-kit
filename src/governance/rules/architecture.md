### Architecture Laws

- **MUST** use stateless service design; state persists in managed stores only
- **MUST** separate API layer from business logic (no direct DB calls in handlers)
- **MUST NOT** introduce circular dependencies between modules
- **MUST** design for horizontal scalability
- **MUST** use dependency injection for testability
