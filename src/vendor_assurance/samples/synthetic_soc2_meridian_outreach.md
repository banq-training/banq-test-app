# SYNTHETIC - FOR TRAINING ONLY

This fabricated report exists only for the hackathon. It describes no real organization, vendor, customer, system, person, or audit.

Vendor: Meridian Patient Outreach
System: Patient Support Call Centre Platform
Data types: PII, PHI
Hosting region: EU West training region
Data residency: Records may be replicated to the US East training region
Sub-processors: None stated
SOC 2 type: Type I
Report date: 2023-11-30

## Independent service auditor-style overview

The fictional Patient Support Call Centre Platform is described here as a deliberately weak example. It exists so reviewers can see what a poor assurance report looks like when the same ten-control checklist is applied. Every observation is invented. Management's description, assertions, exceptions, and conclusions are teaching material rather than an audit opinion.

This report is the counterpart to the stronger examples in this folder. Encryption is adequate, which is common, while governance is where the fictional vendor falls short. That contrast is the teaching point: strong cryptography does not mean a vendor is safe to sign.

## Identity and access management

Access is granted by role, but reviews are ad hoc. MFA is not required for administrator accounts in the example configuration, and shared operator identities remain in use for the fabricated overnight shift. Terminated-user removal is described as a manual process with no simulated evidence of completion.

## Communications and encryption

All connections use TLS 1.2 in transit. Stored records use AES-256 at rest. These two controls are the strongest part of the fictional description and should be cited as such.

## Retention and disposal

There is no defined retention schedule for call recordings or case notes. Product owners intend to approve one at an unspecified future date. Media disposal is not documented, and the fabricated description gives no method, owner, or completion record.

## Security operations

The incident response process commits to notifying affected customers within 96 hours of confirming an incident. Monitoring examples use generated events rather than production telemetry, and no measured response times are provided.

## Supplier management

The fictional vendor states that it uses third parties for telephony and transcription, but no sub-processor list is provided anywhere in the document. Reviewers should treat the absence of the list as the finding rather than inferring the names.

## Privacy requests

There is no process for data subject rights described in this document. The narrative mentions a privacy mailbox but defines no handling for access, correction, and deletion requests.

## Management statement

Management of the fictional training service states that this description is complete for workshop purposes only. Nothing in this document constitutes certification, legal advice, an audit, or a representation about an actual vendor. SYNTHETIC - FOR TRAINING ONLY.
