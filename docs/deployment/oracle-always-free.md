# WIN OS on Oracle Cloud Always Free (the $0 persistent server)

Researched 2026-11-10. Oracle Always Free is the only major free tier that is
a real, always-on VM with no expiry: Ampere A1 ARM, currently **2 OCPU +
12 GB RAM** (Oracle halved it from 4/24 in June 2026), 200 GB block storage,
10 TB/mo egress, Ubuntu images available. The WIN OS stack is multi-arch
(PostGIS, Redis, Prometheus, Grafana, Mosquitto, Python images all publish
arm64), so ARM is not a blocker.

Catches, honestly:
- Signup requires Stephen personally: a physical credit/debit card (no
  prepaid/virtual) for identity verification (small temporary hold, released;
  Always Free resources are never charged) + phone SMS verification + strict
  fraud screening. Muse cannot and will not handle card details - this step
  is the account owner's, in his own browser.
- Home region is permanent for Always Free. Pick **US East (Ashburn)** or
  **US Midwest (Chicago)** - both usually have A1 capacity. If A1 is out of
  capacity at first, the 2 AMD micro VMs (1 GB each) are too small for the
  full stack; retry A1 rather than settling.
- Idle reclamation: Oracle may reclaim instances idle (<20% CPU/network/
  memory) for 7 straight days. A running WIN OS stack with monitoring is
  normally above that on memory; note it anyway.

## Stephen's 10-minute signup (only he can do this part)
1. oracle.com/cloud/free -> Start for free. Email + country; verify email.
2. Phone SMS verification; then card verification (temporary hold only).
3. Home region: US East (Ashburn). Account type: keep Free Tier (do NOT
   upgrade to Pay-As-You-Go; not needed and it changes billing behaviour).
4. Console -> Compute -> Instances -> Create instance:
   - Name: win-os-core
   - Image: Canonical Ubuntu 24.04 (aarch64)
   - Shape: Ampere VM.Standard.A1.Flex, 2 OCPU, 12 GB
   - Networking: new VCN with public subnet; assign public IPv4
   - SSH key: choose "Paste public key" and paste the key Muse provided
     in chat (it lets Muse deploy; Stephen keeps full console admin and
     can remove the key at any time)
   - Boot volume: 100 GB
5. Security list (in the VCN): ingress 22/tcp (his IP ideally, 0.0.0.0/0 if
   unsure), 80/tcp, 443/tcp from 0.0.0.0/0. Nothing else inbound - Postgres,
   Redis, MQTT and monitoring stay private behind the stack's own rules.
6. Send Muse the instance public IP (and nothing else - no passwords, no
   card anything; there is no password, access is by SSH key).

## What Muse does the moment the IP arrives (no further cost, no prompts)
1. SSH in as ubuntu; run the Ansible site playbook for real (validate +
   Docker roles) against the instance.
2. Clone branch win-os/initial-platform to /opt/win-os; create .env with
   generated secrets stored ONLY on the server in /opt/win-os/.env and a
   root-only /opt/win-os/CREDENTIALS.txt (Stephen reads it over SSH; secrets
   are never posted in chat).
3. Preflight, Alembic migrations, `docker compose up` (core + intelligence
   + monitoring + edge), systemd unit enabled so the stack survives reboot.
4. TLS: point the IP at a sslip.io hostname (e.g. <ip-dashed>.sslip.io) and
   issue a real Let's Encrypt certificate via certbot with the shipped
   nginx template. If Stephen later points a real domain at it, the cert is
   re-issued for that name in minutes.
5. Seed the labelled demo dataset, run verify-deployment.sh against the
   public HTTPS URL, publish the URLs + a verification report, and update
   the release-readiness doc: at that point every remaining item except a
   physical edge device is verified, and the edge bridge can be exercised
   against the live broker with labelled simulated telemetry.
