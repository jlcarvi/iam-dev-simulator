# Serverless Event-Driven AWS IoT Device Simulator

A production-ready, fully serverless IoT device simulator built on AWS using the **Serverless Framework** and **Python**. This architecture mimics physical hardware behavior purely through event-driven paradigms, eliminating the need for 24/7 compute servers and dramatically lowering operational costs.

[![AWS](https://shields.io)](https://amazon.com)
[![Serverless](https://shields.io)](https://serverless.com)
[![Python](https://shields.io)](https://python.org)

---

## 🏗️ Architecture Overview

Unlike traditional simulator fleets that require persistent looping server tasks (like EC2 or ECS containers), this architecture uses a **stateless, dual-trigger Lambda strategy** that maps seamlessly to real physical hardware components.

### Key Engineering Decisions & Best Practices

* **AWS IoT Device Shadows vs. Databases:** Chosen over traditional databases like DynamoDB to leverage native cloud/hardware synchronization state engines (`desired` vs. `reported` JSON payloads) and prevent race conditions via built-in shadow state `version` increments.
* **Dual-Trigger Execution Model:** A single Lambda handles two completely independent asynchronous workloads, keeping the codebase unified:
  1. **Reactive Mode (IoT Rule):** Fires only on a `shadow/update/delta` message, acting as physical microchip actuators updating state.
  2. **Proactive Mode (EventBridge Cron):** Fires on a fixed cron schedule to broadcast environmental mock sensor streams (telemetry) to an explicit topic.
* **No-Certificate IAM Authentication:** Simulates device interactions over an HTTPS data plane via IAM execution role permissions instead of hardcoded X.509 device keys. This removes security lifecycle overhead while maintaining exact runtime telemetry parity.
* **Connection Re-use Performance Boost:** Pre-warms the `boto3` IoT Data Plane clients globally *outside* the invocation execution loop to dramatically drop API call latency during AWS Lambda warm starts.

---

## 🛠️ Technology Stack & Prerequisites

* **Infrastructure as Code (IaC):** Serverless Framework v4+
* **Runtime Platform:** Python 3.12+
* **AWS Services Utilized:** AWS Lambda, AWS IoT Core (Registry, Rules, Data Plane), Amazon EventBridge (Scheduler), Amazon S3 (Artifact Deployments), IAM Policies.

---

## 📦 Project Directory Structure

```text
├── handler.py          # Core Lambda business logic & hardware orchestration
├── serverless.yml      # Infrastructure-as-Code definitions & cloud event mapping
├── secrets.json        # [LOCAL ONLY] Local environment & deployment configurations
└── .gitignore          # Safeguards secrets, build directories, and Python cache from VCS
```

---

## 🚀 Setup, Local Debugging & Deployment

### 1. Local Configuration (Zero Leaks Environment)
Create a `secrets.json` file in your root folder. This file is explicitly blocked by the `.gitignore` setup to keep infrastructure metadata off your public profile.

```json
{
  "AWS_REGION": "xxxx",
  "AWS_PROFILE": "your-aws-profile-name",
  "DEPLOYMENT_BUCKET": "your-preexisting-s3-deployment-bucket"
}
```

### 2. Sandbox Testing (Local Invocation)
Validate the Lambda handler logic entirely offline before pushing to production:

```bash
# Test Scenario A: Simulating an EventBridge Telemetry Interval
serverless invoke local --function iam-dev-simulator --data '{"thing_name": "Device001"}'

# Test Scenario B: Simulating a Remote Hardware Delta Push Change
serverless invoke local --function iam-dev-simulator --data '{"thing_name": "Device001", "state": {"light": "ON"}}'
```

### 3. Deploying to AWS Production
Compile configurations, bundle the Python script runtime, and provision all resources with a single command:

```bash
serverless deploy
```

---

## 📊 Live Verification

1. Go to the **AWS IoT Core Console** and register an anchor element named `MyVirtualDevice`.
2. Update its shadow **Desired** property block state manually (`"state": {"desired": {"status": "ACTIVE"}}`).
3. Check **CloudWatch Logs** to see the Lambda execute instantly in `shadow_sync` mode and reply with its `reported` state back to the device dashboard loop.

