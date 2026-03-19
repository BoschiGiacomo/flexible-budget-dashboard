# Flexible Budgeting Dashboard

> **Disclaimer:** this tool serves only as a proof of concept and has not been
> tested appropriately. We advise against its use outside of research and
> academic scope. It is not intended for commercial use.

## Overview
This project explores the integration of traditional flexible budgeting
techniques with modern, interactive web frameworks. Built in Python using Dash
and Plotly, the application transitions static financial models into a dynamic
web dashboard. It enables users to manipulate key assumptions, dynamically
explore different financial scenarios, and instantly analyze performance through
interactive visualizations.

Developed as a project for the Emerging Technologies for Accounting and
Accountability course, this tool serves as a proof of concept for integrating
data science into established corporate practices. It aims not only to enhance
traditional managerial accounting techniques, but also to bridge the gap between
complex quantitative frameworks and executive decision-making.

## How to collaborate
Here is a quick guide for the participants on how to collaborate on the project:

Clone the repository

```bash
git clone https://github.com/BoschiGiacomo/flexible-budget-dashboard
cd flexible-budget-dashboard 
```

Create the Virtual Environement

```bash
python -m venv .venv # You might have to use python3 if python doesn't work

# On Linux/macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

## How to commit to the project (Git Workflow)

**Why don't we push directly to `main`?**
If everyone edits the main code at the same time, we will overwrite each other's
work and the risks of conflicts and breaking the code become higher. By creating
your own branch, you get a private, safe sandbox. You can experiment, make
mistakes, and save your code without any fear of breaking the working codebase. 

Here is the step-by-step workflow:
1. **Get the latest code:** `git checkout main` then `git pull`
2. **Create your local repository:** `git checkout -b your-branch-name`
3. **Write your Python code and save the files**
4. **Save to Git:** `git add .` followed by `git commit -m "brief summary of changes"`
5. **Send it to GitHub:** `git push origin your-branch-name`
6. **Visit GitHub.com, go to your branch and click "Compare & Pull Request"** so
   we can review the changes together
