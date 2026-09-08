# CI trigger policy

Normal pushes, pull requests and manual dispatches run qualification. Because some GitHub App content writes do not emit observable push workflow runs, maintainers may open an Issue whose title begins with `[CI]` to run the same four-platform qualification on `main` without creating a branch. The workflow reports the result to the Issue, refreshes the public-source manifest only after qualification succeeds, and keeps all physical/engineering approvals `NOT_EVALUATED`.
