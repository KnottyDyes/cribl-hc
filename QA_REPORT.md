# QA Report
Thu Jan  1 16:00:02 UTC 2026


## Git context

Command:

```sh
git config --global --add safe.directory /work || true; git status -sb || true
```

## feature/core-api-integration...origin/feature/core-api-integration
 A ._.DS_Store
 A ._requirements.txt
 A API_PHASE1_COMPLETE.md
 A BATCH_1_SUMMARY.md
 A BATCH_2_POLISH_SUMMARY.md
 A BATCH_2_SUMMARY.md
 A CLEAN_CONFIG_FEATURE.md
 A CREDENTIAL_MANAGEMENT.md
 A CREDENTIAL_STORAGE_IMPLEMENTATION.md
 A DEBUG_MODE_IMPLEMENTATION_SUMMARY.md
 A DEBUG_MODE_USAGE.md
 A EDGE_TEST_SUMMARY.md
 A ENHANCEMENTS_PRODUCT_TAGS_SORTING.md
 A FRONTEND_IMPROVEMENTS.md
 A GUI_IMPLEMENTATION_PLAN.md
 A HEALTH_ANALYZER_ENHANCEMENTS.md
 A LAKE_SEARCH_API_RESEARCH.md
 A MVP_COMPLETION_SUMMARY.md
 A PERFORMANCE_VALIDATION.md
 A PHASE_2_FRONTEND_COMPLETE.md
 A PHASE_2_PREPARATION_COMPLETE.md
 A PR_REVIEW.md
 A QUICK_START_TESTING.md
 A SUMMARY.md
 A TEST_BATCHES.md
 A TEST_COVERAGE_REPORT.md
 A TEST_IMPLEMENTATION_FINAL_SUMMARY.md
 A TEST_WORK_SUMMARY.md
 A US3_STORAGE_ANALYZER_COMPLETE.md
 A US4_SECURITY_ANALYZER_COMPLETE.md
 A US5_COST_ANALYZER_COMPLETE.md
 A US6_FLEET_ANALYZER_COMPLETE.md
 A US7_PREDICTIVE_ANALYZER_COMPLETE.md
 M default_report.md
 A docs/._.DS_Store
 A docs/API_INTEGRATION_TEMPLATE.md
 A docs/EDGE_API_MAPPING.md
 A docs/FRONTEND_ARCHITECTURE.md
 A docs/FUTURE_FEATURES.md
 A docs/PHASE1_CLI_COMPLETE.md
 A docs/connection-testing.md
 A docs/cribl_cloud_api_notes.md
 A frontend/._.DS_Store
 A frontend/src/test-types.ts
 M node_modules/.package-lock.json
 D node_modules/@esbuild/darwin-arm64/README.md
 D node_modules/@esbuild/darwin-arm64/bin/esbuild
 D node_modules/@esbuild/darwin-arm64/package.json
 D node_modules/@rollup/rollup-darwin-arm64/README.md
 D node_modules/@rollup/rollup-darwin-arm64/package.json
 D node_modules/@rollup/rollup-darwin-arm64/rollup.darwin-arm64.node
 D node_modules/@tailwindcss/oxide-darwin-arm64/LICENSE
 D node_modules/@tailwindcss/oxide-darwin-arm64/README.md
 D node_modules/@tailwindcss/oxide-darwin-arm64/package.json
 D node_modules/@tailwindcss/oxide-darwin-arm64/tailwindcss-oxide.darwin-arm64.node
 M node_modules/esbuild/bin/esbuild
 D node_modules/lightningcss-darwin-arm64/LICENSE
 D node_modules/lightningcss-darwin-arm64/README.md
 D node_modules/lightningcss-darwin-arm64/lightningcss.darwin-arm64.node
 D node_modules/lightningcss-darwin-arm64/package.json
 A prod_report.md
?? .agent_spec_context.md
?? QA_REPORT.md
?? To
?? scripts/build_spec_context.sh

Exit code: 0

## Python detected


## Python deps (requirements-dev.txt)

Command:

```sh
/opt/venv/bin/python -m pip install -r requirements-dev.txt
```

Collecting httpx>=0.25.0 (from -r /work/requirements.txt (line 5))
  Downloading httpx-0.28.1-py3-none-any.whl.metadata (7.1 kB)
Collecting pydantic>=2.5.0 (from -r /work/requirements.txt (line 8))
  Downloading pydantic-2.12.5-py3-none-any.whl.metadata (90 kB)
Collecting typer>=0.9.0 (from -r /work/requirements.txt (line 11))
  Downloading typer-0.21.0-py3-none-any.whl.metadata (16 kB)
Collecting rich>=13.7.0 (from -r /work/requirements.txt (line 14))
  Downloading rich-14.2.0-py3-none-any.whl.metadata (18 kB)
Collecting structlog>=23.2.0 (from -r /work/requirements.txt (line 17))
  Downloading structlog-25.5.0-py3-none-any.whl.metadata (9.5 kB)
Collecting cryptography>=41.0.0 (from -r /work/requirements.txt (line 20))
  Downloading cryptography-46.0.3-cp311-abi3-manylinux_2_34_x86_64.whl.metadata (5.7 kB)
Collecting python-dateutil>=2.8.0 (from -r /work/requirements.txt (line 23))
  Downloading python_dateutil-2.9.0.post0-py2.py3-none-any.whl.metadata (8.4 kB)
Requirement already satisfied: pytest>=7.4.0 in /opt/venv/lib/python3.11/site-packages (from -r requirements-dev.txt (line 8)) (9.0.2)
Collecting pytest-asyncio>=0.21.0 (from -r requirements-dev.txt (line 9))
  Downloading pytest_asyncio-1.3.0-py3-none-any.whl.metadata (4.1 kB)
Collecting pytest-cov>=4.1.0 (from -r requirements-dev.txt (line 10))
  Downloading pytest_cov-7.0.0-py3-none-any.whl.metadata (31 kB)
Collecting respx>=0.20.0 (from -r requirements-dev.txt (line 13))
  Downloading respx-0.22.0-py2.py3-none-any.whl.metadata (4.1 kB)
Collecting black>=23.12.0 (from -r requirements-dev.txt (line 16))
  Downloading black-25.12.0-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (86 kB)
Requirement already satisfied: ruff>=0.1.9 in /opt/venv/lib/python3.11/site-packages (from -r requirements-dev.txt (line 19)) (0.14.10)
Collecting mypy>=1.7.0 (from -r requirements-dev.txt (line 22))
  Downloading mypy-1.19.1-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.2 kB)
Collecting build>=1.0.0 (from -r requirements-dev.txt (line 25))
  Downloading build-1.3.0-py3-none-any.whl.metadata (5.6 kB)
Collecting twine>=4.0.0 (from -r requirements-dev.txt (line 26))
  Downloading twine-6.2.0-py3-none-any.whl.metadata (3.6 kB)
Collecting anyio (from httpx>=0.25.0->-r /work/requirements.txt (line 5))
  Downloading anyio-4.12.0-py3-none-any.whl.metadata (4.3 kB)
Collecting certifi (from httpx>=0.25.0->-r /work/requirements.txt (line 5))
  Downloading certifi-2025.11.12-py3-none-any.whl.metadata (2.5 kB)
Collecting httpcore==1.* (from httpx>=0.25.0->-r /work/requirements.txt (line 5))
  Downloading httpcore-1.0.9-py3-none-any.whl.metadata (21 kB)
Collecting idna (from httpx>=0.25.0->-r /work/requirements.txt (line 5))
  Downloading idna-3.11-py3-none-any.whl.metadata (8.4 kB)
Collecting h11>=0.16 (from httpcore==1.*->httpx>=0.25.0->-r /work/requirements.txt (line 5))
  Downloading h11-0.16.0-py3-none-any.whl.metadata (8.3 kB)
Collecting annotated-types>=0.6.0 (from pydantic>=2.5.0->-r /work/requirements.txt (line 8))
  Downloading annotated_types-0.7.0-py3-none-any.whl.metadata (15 kB)
Collecting pydantic-core==2.41.5 (from pydantic>=2.5.0->-r /work/requirements.txt (line 8))
  Downloading pydantic_core-2.41.5-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (7.3 kB)
Collecting typing-extensions>=4.14.1 (from pydantic>=2.5.0->-r /work/requirements.txt (line 8))
  Downloading typing_extensions-4.15.0-py3-none-any.whl.metadata (3.3 kB)
Collecting typing-inspection>=0.4.2 (from pydantic>=2.5.0->-r /work/requirements.txt (line 8))
  Downloading typing_inspection-0.4.2-py3-none-any.whl.metadata (2.6 kB)
Collecting click>=8.0.0 (from typer>=0.9.0->-r /work/requirements.txt (line 11))
  Downloading click-8.3.1-py3-none-any.whl.metadata (2.6 kB)
Collecting shellingham>=1.3.0 (from typer>=0.9.0->-r /work/requirements.txt (line 11))
  Downloading shellingham-1.5.4-py2.py3-none-any.whl.metadata (3.5 kB)
Collecting markdown-it-py>=2.2.0 (from rich>=13.7.0->-r /work/requirements.txt (line 14))
  Downloading markdown_it_py-4.0.0-py3-none-any.whl.metadata (7.3 kB)
Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /opt/venv/lib/python3.11/site-packages (from rich>=13.7.0->-r /work/requirements.txt (line 14)) (2.19.2)
Collecting cffi>=2.0.0 (from cryptography>=41.0.0->-r /work/requirements.txt (line 20))
  Downloading cffi-2.0.0-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl.metadata (2.6 kB)
Collecting six>=1.5 (from python-dateutil>=2.8.0->-r /work/requirements.txt (line 23))
  Downloading six-1.17.0-py2.py3-none-any.whl.metadata (1.7 kB)
Requirement already satisfied: iniconfig>=1.0.1 in /opt/venv/lib/python3.11/site-packages (from pytest>=7.4.0->-r requirements-dev.txt (line 8)) (2.3.0)
Requirement already satisfied: packaging>=22 in /opt/venv/lib/python3.11/site-packages (from pytest>=7.4.0->-r requirements-dev.txt (line 8)) (25.0)
Requirement already satisfied: pluggy<2,>=1.5 in /opt/venv/lib/python3.11/site-packages (from pytest>=7.4.0->-r requirements-dev.txt (line 8)) (1.6.0)
Collecting coverage>=7.10.6 (from coverage[toml]>=7.10.6->pytest-cov>=4.1.0->-r requirements-dev.txt (line 10))
  Downloading coverage-7.13.1-cp311-cp311-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl.metadata (8.5 kB)
Collecting mypy-extensions>=0.4.3 (from black>=23.12.0->-r requirements-dev.txt (line 16))
  Downloading mypy_extensions-1.1.0-py3-none-any.whl.metadata (1.1 kB)
Collecting pathspec>=0.9.0 (from black>=23.12.0->-r requirements-dev.txt (line 16))
  Downloading pathspec-0.12.1-py3-none-any.whl.metadata (21 kB)
Collecting platformdirs>=2 (from black>=23.12.0->-r requirements-dev.txt (line 16))
  Downloading platformdirs-4.5.1-py3-none-any.whl.metadata (12 kB)
Collecting pytokens>=0.3.0 (from black>=23.12.0->-r requirements-dev.txt (line 16))
  Downloading pytokens-0.3.0-py3-none-any.whl.metadata (2.0 kB)
Collecting librt>=0.6.2 (from mypy>=1.7.0->-r requirements-dev.txt (line 22))
  Downloading librt-0.7.5-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (1.3 kB)
Collecting pyproject_hooks (from build>=1.0.0->-r requirements-dev.txt (line 25))
  Downloading pyproject_hooks-1.2.0-py3-none-any.whl.metadata (1.3 kB)
Collecting readme-renderer>=35.0 (from twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading readme_renderer-44.0-py3-none-any.whl.metadata (2.8 kB)
Collecting requests>=2.20 (from twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading requests-2.32.5-py3-none-any.whl.metadata (4.9 kB)
Collecting requests-toolbelt!=0.9.0,>=0.8.0 (from twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading requests_toolbelt-1.0.0-py2.py3-none-any.whl.metadata (14 kB)
Collecting urllib3>=1.26.0 (from twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading urllib3-2.6.2-py3-none-any.whl.metadata (6.6 kB)
Collecting keyring>=21.2.0 (from twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading keyring-25.7.0-py3-none-any.whl.metadata (21 kB)
Collecting rfc3986>=1.4.0 (from twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading rfc3986-2.0.0-py2.py3-none-any.whl.metadata (6.6 kB)
Collecting id (from twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading id-1.5.0-py3-none-any.whl.metadata (5.2 kB)
Collecting pycparser (from cffi>=2.0.0->cryptography>=41.0.0->-r /work/requirements.txt (line 20))
  Downloading pycparser-2.23-py3-none-any.whl.metadata (993 bytes)
Collecting SecretStorage>=3.2 (from keyring>=21.2.0->twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading secretstorage-3.5.0-py3-none-any.whl.metadata (4.0 kB)
Collecting jeepney>=0.4.2 (from keyring>=21.2.0->twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading jeepney-0.9.0-py3-none-any.whl.metadata (1.2 kB)
Collecting importlib_metadata>=4.11.4 (from keyring>=21.2.0->twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading importlib_metadata-8.7.1-py3-none-any.whl.metadata (4.7 kB)
Collecting jaraco.classes (from keyring>=21.2.0->twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading jaraco.classes-3.4.0-py3-none-any.whl.metadata (2.6 kB)
Collecting jaraco.functools (from keyring>=21.2.0->twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading jaraco_functools-4.4.0-py3-none-any.whl.metadata (3.0 kB)
Collecting jaraco.context (from keyring>=21.2.0->twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading jaraco_context-6.0.2-py3-none-any.whl.metadata (4.3 kB)
Collecting zipp>=3.20 (from importlib_metadata>=4.11.4->keyring>=21.2.0->twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading zipp-3.23.0-py3-none-any.whl.metadata (3.6 kB)
Collecting mdurl~=0.1 (from markdown-it-py>=2.2.0->rich>=13.7.0->-r /work/requirements.txt (line 14))
  Downloading mdurl-0.1.2-py3-none-any.whl.metadata (1.6 kB)
Collecting nh3>=0.2.14 (from readme-renderer>=35.0->twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading nh3-0.3.2-cp38-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (2.0 kB)
Collecting docutils>=0.21.2 (from readme-renderer>=35.0->twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading docutils-0.22.4-py3-none-any.whl.metadata (15 kB)
Collecting charset_normalizer<4,>=2 (from requests>=2.20->twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading charset_normalizer-3.4.4-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (37 kB)
Collecting more-itertools (from jaraco.classes->keyring>=21.2.0->twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading more_itertools-10.8.0-py3-none-any.whl.metadata (39 kB)
Collecting backports.tarfile (from jaraco.context->keyring>=21.2.0->twine>=4.0.0->-r requirements-dev.txt (line 26))
  Downloading backports.tarfile-1.2.0-py3-none-any.whl.metadata (2.0 kB)
Downloading httpx-0.28.1-py3-none-any.whl (73 kB)
Downloading httpcore-1.0.9-py3-none-any.whl (78 kB)
Downloading pydantic-2.12.5-py3-none-any.whl (463 kB)
Downloading pydantic_core-2.41.5-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (2.1 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.1/2.1 MB 7.2 MB/s  0:00:00
Downloading typer-0.21.0-py3-none-any.whl (47 kB)
Downloading rich-14.2.0-py3-none-any.whl (243 kB)
Downloading structlog-25.5.0-py3-none-any.whl (72 kB)
Downloading cryptography-46.0.3-cp311-abi3-manylinux_2_34_x86_64.whl (4.5 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.5/4.5 MB 7.6 MB/s  0:00:00
Downloading python_dateutil-2.9.0.post0-py2.py3-none-any.whl (229 kB)
Downloading pytest_asyncio-1.3.0-py3-none-any.whl (15 kB)
Downloading pytest_cov-7.0.0-py3-none-any.whl (22 kB)
Downloading respx-0.22.0-py2.py3-none-any.whl (25 kB)
Downloading black-25.12.0-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (1.8 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.8/1.8 MB 7.2 MB/s  0:00:00
Downloading mypy-1.19.1-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (13.4 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 13.4/13.4 MB 7.7 MB/s  0:00:01
Downloading build-1.3.0-py3-none-any.whl (23 kB)
Downloading twine-6.2.0-py3-none-any.whl (42 kB)
Downloading annotated_types-0.7.0-py3-none-any.whl (13 kB)
Downloading cffi-2.0.0-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (215 kB)
Downloading click-8.3.1-py3-none-any.whl (108 kB)
Downloading coverage-7.13.1-cp311-cp311-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (251 kB)
Downloading h11-0.16.0-py3-none-any.whl (37 kB)
Downloading keyring-25.7.0-py3-none-any.whl (39 kB)
Downloading importlib_metadata-8.7.1-py3-none-any.whl (27 kB)
Downloading jeepney-0.9.0-py3-none-any.whl (49 kB)
Downloading librt-0.7.5-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (184 kB)
Downloading markdown_it_py-4.0.0-py3-none-any.whl (87 kB)
Downloading mdurl-0.1.2-py3-none-any.whl (10.0 kB)
Downloading mypy_extensions-1.1.0-py3-none-any.whl (5.0 kB)
Downloading pathspec-0.12.1-py3-none-any.whl (31 kB)
Downloading platformdirs-4.5.1-py3-none-any.whl (18 kB)
Downloading pytokens-0.3.0-py3-none-any.whl (12 kB)
Downloading readme_renderer-44.0-py3-none-any.whl (13 kB)
Downloading docutils-0.22.4-py3-none-any.whl (633 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 633.2/633.2 kB 5.9 MB/s  0:00:00
Downloading nh3-0.3.2-cp38-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (797 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 797.2/797.2 kB 6.1 MB/s  0:00:00
Downloading requests-2.32.5-py3-none-any.whl (64 kB)
Downloading charset_normalizer-3.4.4-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (151 kB)
Downloading idna-3.11-py3-none-any.whl (71 kB)
Downloading urllib3-2.6.2-py3-none-any.whl (131 kB)
Downloading certifi-2025.11.12-py3-none-any.whl (159 kB)
Downloading requests_toolbelt-1.0.0-py2.py3-none-any.whl (54 kB)
Downloading rfc3986-2.0.0-py2.py3-none-any.whl (31 kB)
Downloading secretstorage-3.5.0-py3-none-any.whl (15 kB)
Downloading shellingham-1.5.4-py2.py3-none-any.whl (9.8 kB)
Downloading six-1.17.0-py2.py3-none-any.whl (11 kB)
Downloading typing_extensions-4.15.0-py3-none-any.whl (44 kB)
Downloading typing_inspection-0.4.2-py3-none-any.whl (14 kB)
Downloading zipp-3.23.0-py3-none-any.whl (10 kB)
Downloading anyio-4.12.0-py3-none-any.whl (113 kB)
Downloading id-1.5.0-py3-none-any.whl (13 kB)
Downloading jaraco.classes-3.4.0-py3-none-any.whl (6.8 kB)
Downloading jaraco_context-6.0.2-py3-none-any.whl (7.0 kB)
Downloading backports.tarfile-1.2.0-py3-none-any.whl (30 kB)
Downloading jaraco_functools-4.4.0-py3-none-any.whl (10 kB)
Downloading more_itertools-10.8.0-py3-none-any.whl (69 kB)
Downloading pycparser-2.23-py3-none-any.whl (118 kB)
Downloading pyproject_hooks-1.2.0-py3-none-any.whl (10 kB)
Installing collected packages: zipp, urllib3, typing-extensions, structlog, six, shellingham, rfc3986, pytokens, pyproject_hooks, pycparser, platformdirs, pathspec, nh3, mypy-extensions, more-itertools, mdurl, librt, jeepney, idna, h11, docutils, coverage, click, charset_normalizer, certifi, backports.tarfile, annotated-types, typing-inspection, requests, readme-renderer, python-dateutil, pytest-asyncio, pydantic-core, mypy, markdown-it-py, jaraco.functools, jaraco.context, jaraco.classes, importlib_metadata, httpcore, cffi, build, black, anyio, rich, requests-toolbelt, pytest-cov, pydantic, id, httpx, cryptography, typer, SecretStorage, respx, keyring, twine

Successfully installed SecretStorage-3.5.0 annotated-types-0.7.0 anyio-4.12.0 backports.tarfile-1.2.0 black-25.12.0 build-1.3.0 certifi-2025.11.12 cffi-2.0.0 charset_normalizer-3.4.4 click-8.3.1 coverage-7.13.1 cryptography-46.0.3 docutils-0.22.4 h11-0.16.0 httpcore-1.0.9 httpx-0.28.1 id-1.5.0 idna-3.11 importlib_metadata-8.7.1 jaraco.classes-3.4.0 jaraco.context-6.0.2 jaraco.functools-4.4.0 jeepney-0.9.0 keyring-25.7.0 librt-0.7.5 markdown-it-py-4.0.0 mdurl-0.1.2 more-itertools-10.8.0 mypy-1.19.1 mypy-extensions-1.1.0 nh3-0.3.2 pathspec-0.12.1 platformdirs-4.5.1 pycparser-2.23 pydantic-2.12.5 pydantic-core-2.41.5 pyproject_hooks-1.2.0 pytest-asyncio-1.3.0 pytest-cov-7.0.0 python-dateutil-2.9.0.post0 pytokens-0.3.0 readme-renderer-44.0 requests-2.32.5 requests-toolbelt-1.0.0 respx-0.22.0 rfc3986-2.0.0 rich-14.2.0 shellingham-1.5.4 six-1.17.0 structlog-25.5.0 twine-6.2.0 typer-0.21.0 typing-extensions-4.15.0 typing-inspection-0.4.2 urllib3-2.6.2 zipp-3.23.0

Exit code: 0

## Ruff missing

Command:

```sh
echo 'ruff not installed in container (unexpected)'
```

ruff not installed in container (unexpected)

Exit code: 0

## Pytest missing

Command:

```sh
echo 'pytest not installed in container (unexpected)'
```

pytest not installed in container (unexpected)

Exit code: 0

## Node detected


## npm ci

Command:

```sh
npm ci
```


added 36 packages, and audited 37 packages in 1s

10 packages are looking for funding
  run `npm fund` for details

found 0 vulnerabilities
npm notice
npm notice New major version of npm available! 10.8.2 -> 11.7.0
npm notice Changelog: https://github.com/npm/cli/releases/tag/v11.7.0
npm notice To update run: npm install -g npm@11.7.0
npm notice

Exit code: 0

## No npm script: lint


## No npm script: format


## No npm script: test


## Git diff (post-run)

Command:

```sh
git diff --stat || true; git status --porcelain || true
```

 ._.DS_Store                                        | Bin 0 -> 120 bytes
 ._requirements.txt                                 | Bin 0 -> 176 bytes
 API_PHASE1_COMPLETE.md                             | 592 +++++++++++++
 BATCH_1_SUMMARY.md                                 | 224 +++++
 BATCH_2_POLISH_SUMMARY.md                          | 245 ++++++
 BATCH_2_SUMMARY.md                                 | 312 +++++++
 CLEAN_CONFIG_FEATURE.md                            | 239 ++++++
 CREDENTIAL_MANAGEMENT.md                           | 368 +++++++++
 CREDENTIAL_STORAGE_IMPLEMENTATION.md               | 427 ++++++++++
 DEBUG_MODE_IMPLEMENTATION_SUMMARY.md               | 287 +++++++
 DEBUG_MODE_USAGE.md                                | 258 ++++++
 EDGE_TEST_SUMMARY.md                               | 277 +++++++
 ENHANCEMENTS_PRODUCT_TAGS_SORTING.md               | 193 +++++
 FRONTEND_IMPROVEMENTS.md                           | 293 +++++++
 GUI_IMPLEMENTATION_PLAN.md                         | 668 +++++++++++++++
 HEALTH_ANALYZER_ENHANCEMENTS.md                    | 225 +++++
 LAKE_SEARCH_API_RESEARCH.md                        | 602 ++++++++++++++
 MVP_COMPLETION_SUMMARY.md                          | 330 ++++++++
 PERFORMANCE_VALIDATION.md                          | 323 ++++++++
 PHASE_2_FRONTEND_COMPLETE.md                       | 457 ++++++++++
 PHASE_2_PREPARATION_COMPLETE.md                    | 382 +++++++++
 PR_REVIEW.md                                       |  36 +
 QUICK_START_TESTING.md                             | 432 ++++++++++
 SUMMARY.md                                         | 253 ++++++
 TEST_BATCHES.md                                    | 325 ++++++++
 TEST_COVERAGE_REPORT.md                            | 252 ++++++
 TEST_IMPLEMENTATION_FINAL_SUMMARY.md               | 439 ++++++++++
 TEST_WORK_SUMMARY.md                               | 210 +++++
 US3_STORAGE_ANALYZER_COMPLETE.md                   | 368 +++++++++
 US4_SECURITY_ANALYZER_COMPLETE.md                  | 630 ++++++++++++++
 US5_COST_ANALYZER_COMPLETE.md                      | 666 +++++++++++++++
 US6_FLEET_ANALYZER_COMPLETE.md                     | 403 +++++++++
 US7_PREDICTIVE_ANALYZER_COMPLETE.md                | 641 ++++++++++++++
 default_report.md                                  |   6 +-
 docs/._.DS_Store                                   | Bin 0 -> 120 bytes
 docs/API_INTEGRATION_TEMPLATE.md                   | 918 +++++++++++++++++++++
 docs/EDGE_API_MAPPING.md                           | 346 ++++++++
 docs/FRONTEND_ARCHITECTURE.md                      | 880 ++++++++++++++++++++
 docs/FUTURE_FEATURES.md                            | 179 ++++
 docs/PHASE1_CLI_COMPLETE.md                        | 291 +++++++
 docs/connection-testing.md                         | 238 ++++++
 docs/cribl_cloud_api_notes.md                      | 135 +++
 frontend/._.DS_Store                               | Bin 0 -> 120 bytes
 frontend/src/test-types.ts                         |  12 +
 node_modules/.package-lock.json                    |  93 ++-
 node_modules/@esbuild/darwin-arm64/README.md       |   3 -
 node_modules/@esbuild/darwin-arm64/bin/esbuild     | Bin 10368562 -> 0 bytes
 node_modules/@esbuild/darwin-arm64/package.json    |  20 -
 node_modules/@rollup/rollup-darwin-arm64/README.md |   3 -
 .../@rollup/rollup-darwin-arm64/package.json       |  22 -
 .../rollup-darwin-arm64/rollup.darwin-arm64.node   | Bin 1813376 -> 0 bytes
 .../@tailwindcss/oxide-darwin-arm64/LICENSE        |  21 -
 .../@tailwindcss/oxide-darwin-arm64/README.md      |   3 -
 .../@tailwindcss/oxide-darwin-arm64/package.json   |  27 -
 .../tailwindcss-oxide.darwin-arm64.node            | Bin 2886000 -> 0 bytes
 node_modules/esbuild/bin/esbuild                   | Bin 10368562 -> 11100344 bytes
 node_modules/lightningcss-darwin-arm64/LICENSE     | 373 ---------
 node_modules/lightningcss-darwin-arm64/README.md   |   1 -
 .../lightningcss.darwin-arm64.node                 | Bin 8002256 -> 0 bytes
 .../lightningcss-darwin-arm64/package.json         |  34 -
 prod_report.md                                     | 915 ++++++++++++++++++++
 61 files changed, 15347 insertions(+), 530 deletions(-)
 A ._.DS_Store
 A ._requirements.txt
 A API_PHASE1_COMPLETE.md
 A BATCH_1_SUMMARY.md
 A BATCH_2_POLISH_SUMMARY.md
 A BATCH_2_SUMMARY.md
 A CLEAN_CONFIG_FEATURE.md
 A CREDENTIAL_MANAGEMENT.md
 A CREDENTIAL_STORAGE_IMPLEMENTATION.md
 A DEBUG_MODE_IMPLEMENTATION_SUMMARY.md
 A DEBUG_MODE_USAGE.md
 A EDGE_TEST_SUMMARY.md
 A ENHANCEMENTS_PRODUCT_TAGS_SORTING.md
 A FRONTEND_IMPROVEMENTS.md
 A GUI_IMPLEMENTATION_PLAN.md
 A HEALTH_ANALYZER_ENHANCEMENTS.md
 A LAKE_SEARCH_API_RESEARCH.md
 A MVP_COMPLETION_SUMMARY.md
 A PERFORMANCE_VALIDATION.md
 A PHASE_2_FRONTEND_COMPLETE.md
 A PHASE_2_PREPARATION_COMPLETE.md
 A PR_REVIEW.md
 A QUICK_START_TESTING.md
 A SUMMARY.md
 A TEST_BATCHES.md
 A TEST_COVERAGE_REPORT.md
 A TEST_IMPLEMENTATION_FINAL_SUMMARY.md
 A TEST_WORK_SUMMARY.md
 A US3_STORAGE_ANALYZER_COMPLETE.md
 A US4_SECURITY_ANALYZER_COMPLETE.md
 A US5_COST_ANALYZER_COMPLETE.md
 A US6_FLEET_ANALYZER_COMPLETE.md
 A US7_PREDICTIVE_ANALYZER_COMPLETE.md
 M default_report.md
 A docs/._.DS_Store
 A docs/API_INTEGRATION_TEMPLATE.md
 A docs/EDGE_API_MAPPING.md
 A docs/FRONTEND_ARCHITECTURE.md
 A docs/FUTURE_FEATURES.md
 A docs/PHASE1_CLI_COMPLETE.md
 A docs/connection-testing.md
 A docs/cribl_cloud_api_notes.md
 A frontend/._.DS_Store
 A frontend/src/test-types.ts
 M node_modules/.package-lock.json
 D node_modules/@esbuild/darwin-arm64/README.md
 D node_modules/@esbuild/darwin-arm64/bin/esbuild
 D node_modules/@esbuild/darwin-arm64/package.json
 D node_modules/@rollup/rollup-darwin-arm64/README.md
 D node_modules/@rollup/rollup-darwin-arm64/package.json
 D node_modules/@rollup/rollup-darwin-arm64/rollup.darwin-arm64.node
 D node_modules/@tailwindcss/oxide-darwin-arm64/LICENSE
 D node_modules/@tailwindcss/oxide-darwin-arm64/README.md
 D node_modules/@tailwindcss/oxide-darwin-arm64/package.json
 D node_modules/@tailwindcss/oxide-darwin-arm64/tailwindcss-oxide.darwin-arm64.node
 M node_modules/esbuild/bin/esbuild
 D node_modules/lightningcss-darwin-arm64/LICENSE
 D node_modules/lightningcss-darwin-arm64/README.md
 D node_modules/lightningcss-darwin-arm64/lightningcss.darwin-arm64.node
 D node_modules/lightningcss-darwin-arm64/package.json
 A prod_report.md
?? .agent_spec_context.md
?? QA_REPORT.md
?? To
?? scripts/build_spec_context.sh

Exit code: 0


# RESULT: PASS

