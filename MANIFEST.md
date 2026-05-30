# Manifest

## App

- `app/04_web_preview/`: FastAPI Web/API and current browser UI
- `app/03_matching_recommendation/`: Oracle context builder and OpenAI recommendation logic
- `app/01_youtube_history/`: YouTube Takeout watch-history importer
- `app/05_local_audio_server/`: gerbera/local audio API reference implementation

## SQL

- `sql/002_revised_schema.sql`: current target schema
- `sql/001_initial_schema.sql`: older initial schema kept for reference

## Deploy

- `deploy/python_ec2/`: Python/FastAPI EC2 setup files
- `deploy/oracle_ec2/`: Oracle EC2 container setup files
- `deploy/client/`: client-side host file helper

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

## Data

- `data/local_library_registration_plan_after_import/`: registration ledger after local library import
