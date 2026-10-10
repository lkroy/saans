#!/usr/bin/env bash
# Saans one-command AWS deploy.
# Usage: ./deploy.sh [stack-name] [region]   (defaults: saans ap-south-1)
#
# Prereqs: AWS account + credentials configured (`aws configure` or env vars),
#          AWS SAM CLI installed. Deploys Lambda + HTTP API + DynamoDB + SNS
#          + the daily 05:30 IST bulletin schedule.
set -euo pipefail

STACK="${1:-saans}"
REGION="${2:-ap-south-1}"
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "==> Staging clean backend copy (excluding .venv, caches)..."
rm -rf "$ROOT/build"
mkdir -p "$ROOT/build/backend"
rsync -a --delete \
  --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' --exclude '.git' \
  "$ROOT/../backend/" "$ROOT/build/backend/"

echo "==> sam build..."
cd "$ROOT"
sam build --region "$REGION"

echo "==> sam deploy (stack: $STACK, region: $REGION)..."
PARAMS=()
if [ -n "${GEMINI_API_KEY:-}" ]; then
  PARAMS+=(--parameter-overrides "GeminiApiKey=${GEMINI_API_KEY}")
fi
sam deploy \
  --stack-name "$STACK" \
  --region "$REGION" \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  "${PARAMS[@]}"

echo "==> Done. API URL:"
aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text

echo ""
echo "Frontend: cd ../frontend && VITE_API_URL=<api-url-above> npm run build"
echo "then drag-and-drop frontend/dist into AWS Amplify Hosting."
