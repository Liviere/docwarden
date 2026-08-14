from docwarden.config import DEFAULT_ENV_GLOBS
from docwarden.drift.env_index import build_env_index


def test_env_index_reads_compose_list_style_entries(make_repo):
    root = make_repo({"docker-compose.yml": "services:\n  n8n:\n    environment:\n      - NOTIFY_TO_EMAIL=${NOTIFY_CC_EMAIL}\n"})

    index = build_env_index(root, DEFAULT_ENV_GLOBS)

    assert {"NOTIFY_TO_EMAIL", "NOTIFY_CC_EMAIL"} <= index


def test_env_index_reads_compose_mapping_style_entries(make_repo):
    root = make_repo({"docker-compose.yml": "services:\n  n8n:\n    environment:\n      EXECUTIONS_DATA_PRUNE: 'true'\n"})

    assert "EXECUTIONS_DATA_PRUNE" in build_env_index(root, DEFAULT_ENV_GLOBS)


def test_env_index_reads_env_example_files(make_repo):
    root = make_repo({".env.example": "# comment\nN8N_WEBHOOK_ALLOWED_IPS=127.0.0.1\n"})

    assert "N8N_WEBHOOK_ALLOWED_IPS" in build_env_index(root, DEFAULT_ENV_GLOBS)


def test_env_index_reads_n8n_expression_references(make_repo):
    # n8n workflows cite env vars only inside expression strings — the shell
    # `${VAR}` form never appears there.
    root = make_repo({"n8n/workflows/a.json": '{"url": "={{ $env.HITL_WEBHOOK_URL }}"}\n'})

    assert "HITL_WEBHOOK_URL" in build_env_index(root, DEFAULT_ENV_GLOBS)


def test_env_index_reads_dockerfile_and_shell(make_repo):
    root = make_repo(
        {
            "services/agent/Dockerfile": "ENV OCR_BACKEND=paddle\n",
            "scripts/setup.sh": 'echo "$WG_PEER_KEY"\n',
        }
    )

    index = build_env_index(root, DEFAULT_ENV_GLOBS)

    assert {"OCR_BACKEND", "WG_PEER_KEY"} <= index


def test_env_index_ignores_files_outside_the_globs(make_repo):
    root = make_repo({"src/a.py": "SOME_CONSTANT = 1\n"})

    assert build_env_index(root, DEFAULT_ENV_GLOBS) == set()


def test_env_index_ignores_lowercase_and_too_short_names(make_repo):
    root = make_repo({"docker-compose.yml": "services:\n  a:\n    environment:\n      - lower_case=1\n      - AB=2\n"})

    assert build_env_index(root, DEFAULT_ENV_GLOBS) == set()
