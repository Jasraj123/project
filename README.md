# Personio Employee Export

A lightweight tool that pulls employee data from Personio and writes a clean CSV
for payroll or reporting, plus a per-department summary. It runs on a desktop,
server, or in Docker, and can be scheduled to run daily.

- No hosting required — it writes files to a local folder.
- No credentials in the code — everything lives in `config.yaml`.
- Runs out of the box in **mock mode** with bundled sample data, so you can try
  it before you have API access.

## What it produces

Two files in the `output/` folder:

1. **`personio_employee_export.csv`** — one row per employee with these columns:

   `employeeID, First name, Last name, email, status, Hire date, Termination date,
   position, department, team, Supervisor name, location, Weekly working hours,
   Employment type, Cost center, Base Salary, Last modified`

   - Dates are formatted as `YYYY-MM-DD`.
   - Missing values are left blank.
   - `Base Salary` is normalised to an **annual gross** figure using Personio's
     `fix_salary_interval` (e.g. a monthly amount is multiplied by 12), so values
     are comparable across employees and department averages are meaningful.
   - Salary **currency** is read too: if a department mixes currencies (e.g. a
     multi-country tenant with EUR and GBP), the run logs a warning so the average
     isn't misread. (The fixed CSV schema has no currency column; per-currency
     reporting would be the next step for such customers.)

2. **`department_summary.csv`** — `department, employee_count, average_base_salary`
   (also printed to the console when the tool runs).

## Requirements

- Python 3.9+ (tested on 3.11), or Docker.

## Quick start (mock mode — no credentials needed)

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml     # use_mock_data is true by default
python run_export.py
```

You'll get both CSV files in `output/` using the bundled sample employees.

## Running against real Personio data

1. In Personio, go to **Settings > Integrations > API credentials** and
   **Generate new credentials**. Give the credential **read** access to
   Employees and whitelist the employee attributes used in the CSV
   (name, email, status, hire/termination date, position, department, team,
   supervisor, office, weekly hours, employment type, cost center, fixed salary).
2. Copy the **Client ID** and **Client Secret** into `config.yaml`.
3. Set `use_mock_data: false`.
4. Run it:

```bash
python run_export.py
```

### Which API is used

The tool calls the Personio **v1 Employee endpoint**
(`GET /v1/company/employees`) after authenticating at `POST /v1/auth`.
This endpoint returns all the master data, employment details, and the fixed
salary this export needs in one place, which keeps the integration simple.
Personio enforces pagination on this endpoint with a **maximum of 100 records
per page**, so the client fetches page by page (following the response
`metadata`) until every employee has been retrieved. The parsing logic lives in
`personio_export/transform.py` and is shared by both mock and live data.

#### Why v1 (and not v2)

The brief asks us to decide between v1 and v2. For this use case v1 is the
pragmatic choice:

- **Everything in one call.** v1 `/company/employees` returns master data,
  employment details and fixed salary together, so the whole CSV comes from a
  single, well-understood request.
- **Simplest auth to hand to a customer.** v1 uses a client-ID/secret exchange
  for a bearer token that is **stable for 24 hours** — no per-request token
  rotation to implement or explain.
- **Stable and documented.** The pagination and salary fields are well
  established, which suits a tool a customer maintains themselves.

**When I'd move to v2:** if the customer needs the newer OAuth 2.0 flow,
finer-grained scopes, or the richer/normalised v2 data model (or other data such
as absences at scale). Because extract, transform and load are separate modules,
switching means changing only `client.py` — the transform and CSV output stay
the same.

## Configuration

All settings live in `config.yaml` (copied from `config.example.yaml`):

| Key | Meaning |
| --- | --- |
| `personio.base_url` | API base URL (default `https://api.personio.de`). |
| `personio.client_id` / `client_secret` | Your API credentials. |
| `export.output_dir` | Folder for the CSV files (created if missing). |
| `export.employee_file` / `summary_file` | Output file names. |
| `use_mock_data` | `true` = sample data, `false` = call the live API. |

## Running daily (scheduling)

The tool does one run per invocation and overwrites the CSVs with fresh data,
so schedule it with whatever your environment already has:

- **macOS/Linux (cron)** — run every day at 06:00:

  ```
  0 6 * * *  cd /path/to/personio && /usr/bin/python3 run_export.py >> export.log 2>&1
  ```

- **Windows** — use Task Scheduler to run `python run_export.py` daily.

## Running with Docker

```bash
docker build -t personio-export .

# Mount your config and an output folder so nothing sensitive is baked in.
docker run --rm \
  -v "$PWD/config.yaml:/app/config.yaml:ro" \
  -v "$PWD/output:/app/output" \
  personio-export
```

## Built for real customers

- **Scales to large companies.** Employees are fetched page by page (100 per
  page, the API maximum), so a 2,000-employee company is handled the same as a
  small one.
- **Resilient.** Transient failures and rate limits are retried automatically
  with exponential backoff before the run gives up.
- **Transparent.** Every run ends with a data-quality summary (headcount and any
  missing email/department/salary values) so problems are caught early.

## Project structure

```
run_export.py              # CLI entry point (orchestrates the run)
config.example.yaml        # template config; copy to config.yaml
requirements.txt
Dockerfile
docs/architecture.md       # architecture diagram + design notes
personio_export/
  config.py                # load & validate config
  client.py                # authenticate + fetch employees (paginate + retry)
  transform.py             # JSON -> CSV rows + department summary
  exporter.py              # write CSV files
  report.py                # run summary + data-quality checks
  sample_data.py           # bundled sample data for mock mode
tests/
  test_transform.py        # unit tests for the transform logic
```

See `docs/architecture.md` for a diagram of how the pieces fit together.

## Running the tests

No extra packages needed - the tests use Python's built-in `unittest`:

```bash
python -m unittest
```

## Development

Linting/formatting uses [ruff](https://docs.astral.sh/ruff/) (config in
`pyproject.toml`). Install the dev tooling and run the same checks CI runs:

```bash
pip install -r requirements-dev.txt
ruff check .            # lint
ruff format --check .   # formatting
python -m unittest      # tests
```

Every push and pull request runs these on Python 3.9 and 3.11 via GitHub Actions
(`.github/workflows/ci.yml`).

## Troubleshooting

| Message | Cause | Fix |
| --- | --- | --- |
| `Config file not found` | No `config.yaml`. | Copy `config.example.yaml` to `config.yaml`. |
| `API token missing` | `client_id`/`client_secret` empty with `use_mock_data: false`. | Add credentials, or set `use_mock_data: true`. |
| `Authentication failed (401)` | Wrong client ID/secret. | Re-check the values from Settings > API credentials. |
| `Access denied (403)` | Credential lacks permissions or attributes aren't whitelisted. | Enable read access and whitelist the needed employee attributes. |
| `Could not reach Personio` | Network/firewall/proxy issue. | Check connectivity to `api.personio.de`. |
| `Personio rejected the request parameters (422)` | Page size above the API limit. | Keep `PAGE_SIZE` at 100 or below (the v1 endpoint's maximum). |
| `Cannot write CSV file` / `Cannot create output folder` | No write permission for `output_dir`. | Point `output_dir` to a writable folder or fix permissions. |
| Some columns are blank | Attribute not whitelisted, or not set on the employee. | Whitelist the attribute in Personio; blanks are expected for unset fields. |

## Security notes

- **Keep secrets out of code and git.** Credentials live only in `config.yaml`,
  which is listed in `.gitignore`. Never commit it.
- **Least privilege.** Give the API credential **read-only** access and only the
  attributes this export needs.
- **Protect the output.** Exported CSVs contain personal and salary data. Store
  them in a restricted folder and delete them when no longer needed.
- **Secure delivery.** If you forward files (e.g. to an SFTP server), use an
  encrypted transport; don't email unencrypted HR data.
- **Rotate credentials** periodically and whenever someone with access leaves.
