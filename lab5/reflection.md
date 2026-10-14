# Lab 5: Reflection on Static Code Analysis

## Question 1: What is the purpose and scope of static code analysis, and how does it differ from dynamic testing?

Static code analysis (SCA) is the method of examining software source code without executing the program. Its scope encompasses code quality enforcement, structural validation, adherence to style guidelines (such as PEP 8), detection of anti-patterns, and the identification of known security vulnerabilities (such as injection flaws and insecure function calls).

In contrast, dynamic testing (such as unit tests, integration tests, and end-to-end testing) executes compiled or interpreted code against predefined runtime test vectors to verify behavioral correctness and performance. 

**Key differences:**
- **Execution:** Static analysis analyzes the syntax tree and control/data flow statically at rest; dynamic testing requires an executable build and running test environment.
- **Coverage & Edge Cases:** Static analysis checks 100% of the visible codebase, including error paths and exception handlers that are rarely triggered during manual or dynamic testing.
- **Feedback Speed & Cost:** Static analysis provides instantaneous feedback during development (shifting defects left), which significantly lowers remediation costs compared to defects discovered during QA or production.

---

## Question 2: How do Pylint, Flake8, and Bandit complement each other in a Python development workflow?

Each of the three tools serves a distinct, specialized role in maintaining a robust codebase:

1. **Bandit ("The Security Guard"):**
   - Focuses strictly on cybersecurity vulnerabilities, dangerous functions, and common security weaknesses (CWEs).
   - In our script, Bandit immediately flagged `eval()` (B307: Arbitrary Code Execution / CWE-78) and bare `try-except-pass` blocks (B110: Exception Suppression / CWE-703).
   - Its strength is preventing exploit vectors before deployment.

2. **Flake8 ("The Grammar & Style Checker"):**
   - Focuses on fast, lightweight linting and strict adherence to PEP 8 style standards, line lengths, blank line requirements, and basic syntax/import errors.
   - In our script, Flake8 identified unused imports (`math`, `sys`), missing double blank lines around top-level functions (E302, E305), and direct singleton equality checks (`== True` vs. idiomatic truthiness).
   - Its strength is readability, developer consistency, and clean code hygiene.

3. **Pylint ("The Strict Code Reviewer"):**
   - Performs deep semantic analysis, checking design patterns, cyclomatic complexity, mutable default arguments, missing documentation (docstrings), proper naming conventions, and resource management.
   - In our script, Pylint flagged dangerous mutable defaults (`logs=[]`), unclosed file descriptors without context managers (`open()` without `with`), string formatting opportunities, and shadowed built-ins (`credits`).
   - Its strength is long-term code quality, maintainability, and design sanity.

Together, these tools form a multi-layered defensive pipeline: Bandit guards against security exploits, Flake8 ensures readable and uniform styling, and Pylint enforces architectural design integrity.

---

## Question 3: Discuss the high- and medium-severity issues identified in `scholarship_system.py` and the risks they posed.

1. **Arbitrary Code Execution via `eval(MERIT_FORMULA)` (Medium Severity / CWE-78):**
   - *Risk:* In Python, `eval()` executes any string expression with full interpreter privileges. Because `scholarship_system.py` invited user input via `formula = input(...)` and passed it to `change_formula()`, an external user could supply a payload such as `__import__('os').system('rm -rf /')` or execute data exfiltration scripts.
   - *Resolution:* We replaced arbitrary `eval()` execution with an Abstract Syntax Tree (`ast`) evaluator (`_safe_eval_formula`). By whitelisting safe arithmetic nodes (`ast.Add`, `ast.Sub`, `ast.Mult`, `ast.Div`, `ast.USub`) and numeric/identifier nodes, arbitrary function calls or OS interactions are rejected at parse time with a `ValueError`.

2. **Mutable Default Argument `logs=[]` (Design Flaw / High Runtime Risk):**
   - *Risk:* In Python, default argument expressions are evaluated once when the function is defined, not each time the function is called. When a mutable object (like a list `[]` or dict `{}`) is used as a default, that single object instance is retained across all subsequent invocations where the argument is omitted. In `evaluate_applicant()`, this caused applicant log messages to accumulate across separate screening runs, creating cross-student data leakage and race conditions.
   - *Resolution:* We updated the signature to `logs: Optional[List[str]] = None` and created a fresh `logs = []` instance within the function scope when `logs is None`.

3. **Silent Exception Swallowing (`try: ... except: pass`) (CWE-703):**
   - *Risk:* A bare `except:` block without an exception type catches every possible exception, including `KeyboardInterrupt`, memory errors, system exits, permission errors, and invalid JSON formatting. Catching and silently passing makes bugs invisible and corrupt data impossible to trace.
   - *Resolution:* We caught specific, recoverable exceptions (`FileNotFoundError`, `json.JSONDecodeError`, `OSError`) and ensured deterministic file closing with `with open(..., encoding="utf-8")`.

---

## Question 4: How does integrating static code analysis into a CI/CD pipeline contribute to software quality and maintainability?

Integrating static code analysis directly into modern automated pipelines (such as GitHub Actions, GitLab CI, or pre-commit git hooks) provides substantial systemic benefits:

1. **Automated Quality Gates:** Pull requests can be automatically blocked if code style degrades, new security vulnerabilities are introduced, or Pylint scores drop below established thresholds (e.g. 9.5/10.0).
2. **Reduced Cognitive Load during Peer Reviews:** Human code reviewers can focus on business logic, high-level architecture, and algorithm correctness rather than arguing about PEP 8 whitespace, unused imports, or formatting choices.
3. **Prevention of Technical Debt:** Eliminating anti-patterns early prevents technical debt from accumulating, making code refactoring safer and onboarding new developers significantly faster.
4. **Enhanced Security Posture (DevSecOps):** By scanning dependencies and code for vulnerabilities at commit time, organizations achieve continuous compliance and minimize the risk of zero-day exploits reaching production environments.
