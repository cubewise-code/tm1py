# TM1py Documentation Guide

This guide explains how to work with the TM1py documentation, including the tools and processes used, how to test changes locally, and how the deployment workflow operates.

## Technology Stack

The TM1py documentation is built using the following tools:

- **[MkDocs](https://www.mkdocs.org/):** A static site generator for project documentation.
- **[Mike](https://github.com/jimporter/mike):** A tool for managing versioned documentation with MkDocs.
- **GitHub Actions:** Automates the deployment of the documentation to the `gh-pages` branch.

## How to Modify the Documentation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/cubewise-code/tm1py.git
   cd tm1py

2. **Install Development Dependencies:**

    Install the required dependencies for working with the documentation:

    ```bash
    pip install -e .[dev]
    pip install -r docs/requirements-docs.txt
    ```

3. **Edit the Documentation:**

    - The documentation files are located in the docs/ folder.
    - Common files to edit:
        - index.md: The main landing page.
        - getting-started.md: Instructions for getting started with TM1py.
        - how-to-contribute.md: Contribution guidelines.
        - links.md: Useful links related to TM1py.

4. **Test Locally:**

    You can preview the documentation locally using MkDocs:

    ```bash
    mkdocs serve
    ```

    Open your browser and navigate to <http://127.0.0.1:8000/> to view the documentation.

## Deployment Workflow

The documentation is automatically deployed to the gh-pages branch using GitHub Actions. The deployment process is triggered in the following scenarios:

1. **Push to `master`:**

    When changes are pushed to the `master` branch, the documentation is deployed as the latest version.

2. **Tagging a Commit:**

    When a commit is tagged with v* (e.g., v1.0.0), the documentation is deployed as a versioned release.

3. **Manual Trigger:**

    The workflow can also be triggered manually via the GitHub Actions interface.

### Deployment Workflow Details

- The workflow is defined in docs.yml.
- It performs the following steps:
    1. Checks out the repository.
    2. Sets up Python and installs dependencies.
    3. Deploys the documentation using mike.
    4. Handles the CNAME file for custom domains.

---

## Important Notes

- Custom Domain:

  - The `CNAME` file, located in the *docs* folder, is automatically copied to the root of the `gh-pages` branch during deployment.
  - Ensure the `CNAME` file is updated if the custom domain changes.

Testing Changes:

Always test your changes locally using mkdocs serve before pushing to master.

---

## Example Workflow

Here’s an example of how you might update the documentation:

1. Edit `getting-started.md` to add new instructions.
2. Test the changes locally:

    ```bash
    mkdocs serve
    ```

3. Commit and push the changes:

4. Create a merge request

5. After merge to master:The GitHub Actions workflow will automatically deploy the updated documentation.
