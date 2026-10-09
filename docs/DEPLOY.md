# Saans — Deploy Guide (AWS free tier)

You don't need any of this for prize eligibility (Strands Agents SDK already
covers that) — this is for the live URL.

## Option A: full serverless (recommended, ~20 min)

Prereqs: AWS account (free tier; signup needs a debit/RuPay card, ~₹2 verification
charge), AWS CLI + SAM CLI installed, `aws configure` done.

```bash
cd infra
sam build
sam deploy --guided   # accept defaults; note the API Gateway URL it prints
```

What you get: Lambda (FastAPI via Mangum) + HTTP API Gateway, DynamoDB table
`saans-schools`, EventBridge Scheduler rule firing the bulletin Lambda daily at
05:30 Asia/Kolkata, SNS topic `saans-alerts`. All within free-tier limits for a
demo.

Swap the in-memory school store for DynamoDB: the Lambda handler reads the table
name from `SCHOOLS_TABLE` env (see `infra/template.yaml`); point
`backend/app/stores.py` at boto3 when that env var is present.

## Option B: frontend on Amplify Hosting (~5 min)

```bash
cd frontend
VITE_API_URL=https://<your-api-gateway-url> npm run build
```

AWS Console → Amplify → Host web app → drag-and-drop `frontend/dist`.
You get a `https://…amplifyapp.com` URL for the demo video and submission.

## Option C: local demo (zero AWS)

Exactly the Quickstart in the README. The judges score local and deployed
projects "with the same care" — a flawless local demo beats a broken deploy.
