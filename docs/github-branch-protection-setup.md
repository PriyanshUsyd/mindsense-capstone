# Enabling Branch Protection on `main` (2 minutes)

For whoever has admin access on `github.com/PriyanshUsyd/mindsense-capstone`.
Web UI only — nothing here can be done from a commit or the CLI without `gh`.

1. Open **github.com/PriyanshUsyd/mindsense-capstone** → **Settings** tab
   (top of the repo page, not your account settings).
2. In the left sidebar, click **Branches**.
3. Next to "Branch protection rules", click **Add branch protection rule**
   (a.k.a. **Add rule**).
4. In **Branch name pattern**, type: `main`
5. Check **Require a pull request before merging**.
   - Under it, check **Require approvals** and set the number to `1`.
6. Check **Require status checks to pass before merging**.
   - Check **Require branches to be up to date before merging**.
   - *(No CI workflow exists yet — leave the status-check search box empty
     for now. Once a CI workflow is added, come back here and select it,
     otherwise this checkbox has nothing to enforce yet.)*
7. (Recommended) Check **Do not allow bypassing the above settings** so
   the rule also applies to repo admins, not just everyone else.
8. Scroll down, click **Create** (or **Save changes** if editing an
   existing rule).

Done. Anyone — including admins, if step 7 was checked — must now open a
pull request into `main` and get at least one approval before merging,
instead of pushing straight to `main`.
