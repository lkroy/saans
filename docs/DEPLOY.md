# Saans — Deploy Guide (AWS free tier)

You don't need any of this for prize eligibility (Strands Agents SDK already
covers that) — this is for the live URL.

## One-command deploy

```bash
cd infra
./deploy.sh            # defaults: stack "saans", region ap-south-1 (Mumbai)
./deploy.sh mystack eu-west-1   # custom stack / region
```

Prereqs: AWS account (free tier; signup needs a debit/RuPay card, ~₹2
verification charge) + credentials configured (`aws configure` or `AWS_*` env
vars) + SAM CLI. The script stages a clean backend copy (no `.venv`), runs
`sam build`, then `sam deploy`. Set `GEMINI_API_KEY` in your env first if you
want the live Strands agent instead of the rule-based fallback.

What you get: Lambda (FastAPI via Mangum, Python 3.12) + HTTP API Gateway,
DynamoDB table `saans-schools` (the app auto-switches from in-memory to
DynamoDB when `SCHOOLS_TABLE` is set), EventBridge Scheduler firing the
bulletin Lambda daily at 05:30 Asia/Kolkata, SNS topic `saans-alerts` (bulletins
published there when `ALERTS_TOPIC_ARN` is set). All within free-tier limits
for a demo. The script prints the API URL at the end.

## Frontend → Amplify Hosting (~5 min)

```bash
cd frontend
VITE_API_URL=https://<api-url-from-deploy> npm run build
```

AWS Console → Amplify → Host web app → drag-and-drop `frontend/dist`.
You get a `https://…amplifyapp.com` URL for the demo video and submission.

## Local demo (zero AWS)

Exactly the Quickstart in the README. The judges score local and deployed
projects "with the same care" — a flawless local demo beats a broken deploy.
