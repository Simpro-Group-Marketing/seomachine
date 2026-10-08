## Repository Development Rules

These rules apply to code, tests, configuration, scripts, commands, and developer documentation. They supplement the proof-sensitive content and workflow rules elsewhere in this file.

### Before Editing

- Inspect the relevant implementation, tests, configuration, and current working-tree diff before editing.
- State material assumptions. Do not invent repository behavior, test results, data, or requirements.
- Resolve materially different interpretations before editing. For low-risk, reversible ambiguity, choose the simplest interpretation and disclose it.
- Define concise, verifiable success criteria and a verification plan for non-trivial work.

### Implementation Scope

- Make the smallest complete change that satisfies the verified requirement.
- Do not add speculative features, abstractions, configuration, or handling for impossible scenarios.
- Match surrounding repository style and preserve unrelated user changes.
- Do not refactor, reformat, rename, or clean up unrelated code.
- Remove imports, variables, functions, or files only when the current change makes them unused.
- Every changed line must trace directly to the requested outcome or its verification.

### Testing and Verification

- For a bug fix, reproduce the failure with a focused test when practical, then make that test pass.
- For new behavior, test the expected path and relevant invalid inputs.
- Run the narrowest relevant checks first, followed by broader applicable checks.
- Report the commands run, their results, and any checks not run. Never claim validation that was not performed.
- Continue until the success criteria pass or a concrete blocker is proven.
