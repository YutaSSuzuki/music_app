# Manifest

## App

- `app/04_web_preview/`: FastAPI Web/API and current browser UI
- `app/03_matching_recommendation/`: Oracle context builder and OpenAI recommendation logic
- `app/01_youtube_history/`: YouTube Takeout watch-history importer

## SQL

- `sql/002_revised_schema.sql`: current target schema
- `sql/001_initial_schema.sql`: older initial schema kept for reference
- `sql/003_hosted_audio_files.sql`: hosted audio delivery table
- `sql/004_seed_cloud_smoke_test.sql`: three-track cloud delivery smoke-test data
- `sql/005_delete_cloud_smoke_test.sql`: remove three-track smoke-test data

## Deploy

- `deploy/python_ec2/`: Python/FastAPI EC2 setup files
- `deploy/python_ec2/bootstrap_ubuntu.sh`: install Apache, venv support, UFW HTTP rule, and audio directory on Ubuntu
- `deploy/python_ec2/register_hosted_audio.py`: register transferred audio files
- `deploy/python_ec2/check_hosted_audio.py`: validate hosted audio registration
- `deploy/oracle_ec2/`: Oracle Linux 9 RPM setup and legacy container reference files
- `deploy/oracle_ec2/bootstrap_oracle_linux_9.sh`: target Oracle EC2 bootstrap
- `deploy/oracle_ec2/sqlplus_utf8.sh`: run SQL*Plus with UTF-8 client encoding
- `deploy/client/`: client-side host file helper
- `deploy/source/build_hosted_audio_manifest.py`: validate source files and calculate transfer size

## Docs

- `docs/00_migration_plan.md`: staged migration plan
- `docs/01_oracle_ec2_setup.md`: Oracle EC2 setup
- `docs/02_python_ec2_setup.md`: Python EC2 setup
- `docs/03_audio_delivery.md`: audio delivery options
- `docs/04_github_upload_plan.md`: what to upload to GitHub
- `docs/05_operation_commands.md`: operation commands
- `docs/06_next_lambda_s3.md`: later Lambda/S3 plan
- `docs/07_current_state.md`: current zephy DB and runtime state
- `docs/08_current_architecture_and_flow.md`: current architecture and request processing flow
- `docs/09_hosted_audio_cloud_setup.md`: reproduce zephy hosted audio delivery on Python EC2
- `docs/10_zephy_hosted_audio_state.md`: tested zephy hosted audio state

## Data

- `data/local_library_registration_plan_after_import/`: registration ledger after local library import
