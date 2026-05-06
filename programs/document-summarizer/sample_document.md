# Quarterly Engineering Report — Q1

## Overview

This quarter the platform team focused on three initiatives: migrating the
ingestion pipeline to a streaming architecture, hardening authentication,
and reducing infrastructure spend. We shipped 14 production releases
across the period with no Sev-1 incidents.

## Streaming ingestion migration

The legacy batch ingestion job ran on a 15-minute cron and frequently
caused dashboard staleness during traffic spikes. We replaced it with a
Kafka-backed streaming pipeline using a managed Confluent cluster. End-
to-end latency dropped from a median of 7 minutes to under 30 seconds.
Two downstream teams (Search and Billing) have already cut their own
batch jobs over to consume from the new topics.

Outstanding work: backfill for historical data older than 90 days and
schema-registry adoption across all producer services.

## Authentication hardening

We completed the rollout of WebAuthn-based passkeys for staff accounts
and deprecated SMS-based 2FA. 92% of internal users have enrolled at
least one passkey; the remaining 8% are tracked in a follow-up project
with a deadline at the end of next quarter. We also rotated all service
account credentials and moved them to a centralized secrets manager.

## Cost reduction

By right-sizing our Kubernetes node pools and adopting spot instances
for stateless workloads, we reduced compute spend by 23% quarter over
quarter. Storage costs are flat despite a 40% data growth, primarily
due to tiering older logs to cheaper object storage.

## Risks and follow-ups

- Confluent vendor lock-in is a known concern; an exit plan is being
  drafted but has no committed timeline.
- The remaining 8% of users without passkeys represent a long tail of
  service accounts and shared logins that need policy decisions before
  cleanup.
- Spot instance interruptions caused two minor degradations this quarter.
  We are evaluating a small reserved-instance baseline to absorb the
  worst-case interruption windows.

## Headcount and hiring

The team grew from 11 to 14 engineers. Two senior hires joined the
infrastructure pod and one mid-level engineer joined the data-platform
pod. We have one open requisition for a staff-level security engineer
that has been open for the entire quarter.
