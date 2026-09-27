# Code Doctor — IBM Bob / VS Code extension

Analyze the open Python file without leaving the editor:
- Squiggles on slow or insecure lines (N+1, SQL injection, eval, hardcoded secrets, O(n×m) loops)
- Report panel: Scale Score, time/space before → after, speedup at 100k
- IBM Granite fix, verified by the analyzer, applied with one click (undo with Ctrl+Z)

Run: start the backend (see ../HOW-TO-RUN.md), open this `extension` folder in IBM Bob, press **F5**. In the new window, open a Python file and press **Ctrl+Alt+D** (or click the pulse icon at the top right of the editor).
