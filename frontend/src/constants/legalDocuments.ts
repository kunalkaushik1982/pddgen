/**
 * Legal pages for FlowLens (payment / merchant onboarding).
 * Have these reviewed by qualified counsel before high-stakes or regulated use.
 */

export const LEGAL_CONTACT_EMAIL = "kunal.kaushik1982@gmail.com";

/** Correspondence address (India) — shown on Contact and referenced in Terms. */
export const LEGAL_CONTACT_ADDRESS_LINES = [
  "C-1206, Square Arcade",
  "Raj Nagar, Ghaziabad",
  "Pin 201016, Uttar Pradesh, India",
] as const;

export const LEGAL_LAST_UPDATED = "13 April 2026";

export const LEGAL_SLUGS = ["terms", "privacy", "shipping", "contact", "refunds"] as const;
export type LegalSlug = (typeof LEGAL_SLUGS)[number];

export type LegalSection = {
  heading?: string;
  paragraphs: string[];
};

export type LegalDocumentMeta = {
  title: string;
  shortLabel: string;
  sections: LegalSection[];
};

const contactAddressBlock = LEGAL_CONTACT_ADDRESS_LINES.join("\n");

export const LEGAL_DOCUMENTS: Record<LegalSlug, LegalDocumentMeta> = {
  terms: {
    title: "Terms and Conditions",
    shortLabel: "Terms",
    sections: [
      {
        paragraphs: [
          'These Terms and Conditions (“Terms”) govern your access to and use of FlowLens (the “Service”), including our website, web application, and related features that help you turn recordings and transcripts into structured documentation.',
          "The Service is offered from India. By creating an account, placing an order, or using the Service, you agree to these Terms. If you do not agree, do not use the Service.",
          "We may update these Terms from time to time. We will indicate the “Last updated” date on each policy page where we publish material changes. Continued use after the effective date of changes constitutes acceptance of the revised Terms, except where applicable law requires additional consent.",
        ],
      },
      {
        heading: "Operator and contact",
        paragraphs: [
          "Correspondence address for the Service:",
          contactAddressBlock,
          `Support email: ${LEGAL_CONTACT_EMAIL}`,
        ],
      },
      {
        heading: "Eligibility and accounts",
        paragraphs: [
          "You must be legally able to enter a binding contract in your jurisdiction. You agree to provide accurate registration information and to keep your login credentials confidential. You are responsible for activity that occurs under your account unless you notify us promptly of unauthorized use.",
        ],
      },
      {
        heading: "Plans, billing, and taxes",
        paragraphs: [
          "Fees, billing cycles, and included features are described at purchase and in your account where applicable. Amounts may be quoted inclusive or exclusive of applicable taxes (such as GST); taxes are shown at checkout where required.",
          "Payments are processed by our payment partners (including Razorpay). Card and payment data are handled according to the payment provider’s terms and security practices. We do not store full card numbers on our servers when processing is handled by the provider.",
        ],
      },
      {
        heading: "License and acceptable use",
        paragraphs: [
          "We grant you a limited, non-exclusive, non-transferable right to use the Service for your internal business or personal productivity purposes in line with your subscription or plan, unless otherwise agreed in writing.",
          "You will not misuse the Service, including by attempting to probe, scan, or test vulnerabilities; interfere with or disrupt the Service; reverse engineer except where mandatory law allows; upload unlawful content; or use the Service to infringe others’ rights.",
        ],
      },
      {
        heading: "Intellectual property",
        paragraphs: [
          "We and our licensors retain all rights in the Service, software, branding, and documentation. Outputs you generate using the Service from your own inputs remain subject to your rights in those inputs and any license terms shown in the product, except for any third-party materials you provide that remain owned by their respective owners.",
        ],
      },
      {
        heading: "Disclaimer and limitation of liability",
        paragraphs: [
          "The Service is provided on an “as is” and “as available” basis. To the maximum extent permitted by applicable law, we disclaim warranties of merchantability, fitness for a particular purpose, and non-infringement, and we do not warrant uninterrupted or error-free operation.",
          "To the maximum extent permitted by law, our total liability for any claim arising out of or relating to the Service or these Terms is limited to the amount you paid us for the Service in the twelve (12) months before the event giving rise to the claim (or, if greater, what mandatory consumer law requires). We are not liable for indirect, incidental, special, consequential, or punitive damages, or loss of profits, data, or goodwill, except where such exclusion is prohibited by law.",
        ],
      },
      {
        heading: "Suspension and termination",
        paragraphs: [
          "We may suspend or terminate access for breach of these Terms, risk to the Service or other users, or legal requirement. You may stop using the Service at any time. Provisions that by nature should survive (including payment obligations accrued, intellectual property, limitation of liability, and governing law) will survive termination.",
        ],
      },
      {
        heading: "Governing law and disputes",
        paragraphs: [
          "These Terms are governed by the laws of India. Subject to mandatory consumer protections in your jurisdiction, courts at Ghaziabad, Uttar Pradesh, India shall have exclusive jurisdiction over disputes, unless applicable law requires otherwise.",
        ],
      },
    ],
  },
  privacy: {
    title: "Privacy Policy",
    shortLabel: "Privacy",
    sections: [
      {
        paragraphs: [
          "This Privacy Policy explains how we collect, use, disclose, and safeguard personal information when you use FlowLens. By using the Service, you acknowledge this Policy.",
        ],
      },
      {
        heading: "Information we collect",
        paragraphs: [
          "Account and profile: identifiers such as username, email address, and authentication-related data.",
          "Usage and technical data: logs, device/browser type, approximate location derived from IP, timestamps, and interactions with the Service (for example, features used and error reports).",
          "Content you provide: files, transcripts, prompts, and other materials you upload or submit for processing.",
          "Payment-related data: we receive limited information from payment processors (such as transaction status, masked identifiers, and billing metadata). Full card numbers are processed by the payment provider, not stored by us in readable form on our systems when the provider handles card entry.",
        ],
      },
      {
        heading: "How we use information",
        paragraphs: [
          "We use personal information to provide and operate the Service; authenticate users; process transactions and subscriptions; communicate about your account, security, and policy updates; improve reliability and performance; detect abuse and comply with law; and enforce our terms.",
        ],
      },
      {
        heading: "Legal bases (where applicable)",
        paragraphs: [
          "We process personal information as necessary to perform our contract with you; based on our legitimate interests in securing and improving the Service (balanced against your rights); and where required to comply with legal obligations. Where consent is required for specific processing, we will ask for it separately.",
        ],
      },
      {
        heading: "Sharing and subprocessors",
        paragraphs: [
          "We share information with service providers who assist us (for example: hosting, email delivery, analytics, and payment processing including Razorpay). They are permitted to use data only to perform services for us and must protect it appropriately.",
          "We may disclose information if required by law, regulation, legal process, or to protect the rights, safety, and security of users, the public, or the Service.",
        ],
      },
      {
        heading: "Retention",
        paragraphs: [
          "We retain personal information for as long as your account is active and as needed to provide the Service, meet legal, tax, and accounting requirements, resolve disputes, and enforce agreements. Retention periods may vary by data category and jurisdiction.",
        ],
      },
      {
        heading: "Security",
        paragraphs: [
          "We implement technical and organizational measures appropriate to the risk, including access controls and encryption in transit where standard for the Service. No method of transmission or storage is completely secure; we cannot guarantee absolute security.",
        ],
      },
      {
        heading: "Your choices and rights",
        paragraphs: [
          "Depending on applicable law (including India’s Digital Personal Data Protection Act, 2023 where applicable), you may have rights to access, correction, erasure, restriction, objection, or portability. To exercise rights, contact us using the details on the Contact page. You may withdraw consent where processing is consent-based, without affecting prior lawful processing.",
        ],
      },
      {
        heading: "Children",
        paragraphs: [
          "The Service is not directed to children under the age required by applicable law to consent without parental authorization. We do not knowingly collect personal information from such children.",
        ],
      },
      {
        heading: "International transfers",
        paragraphs: [
          "If we transfer personal information outside India, we will do so with appropriate safeguards as required by applicable law.",
        ],
      },
      {
        heading: "Contact",
        paragraphs: [
          `Privacy-related requests: ${LEGAL_CONTACT_EMAIL}`,
          "Correspondence address:",
          contactAddressBlock,
        ],
      },
    ],
  },
  shipping: {
    title: "Shipping & Delivery Policy",
    shortLabel: "Shipping",
    sections: [
      {
        paragraphs: [
          "FlowLens delivers software-based services and digital outputs through your account. We do not ship physical products unless a specific offering explicitly states otherwise.",
        ],
      },
      {
        heading: "Digital delivery",
        paragraphs: [
          "Service access, generated documents, exports, downloads, and entitlements are delivered electronically through the application when processing completes or when your subscription status allows access.",
          "Delivery is tied to successful authentication to your account. You are responsible for maintaining accurate email and account settings so that we can communicate about your access and orders.",
        ],
      },
      {
        heading: "Timelines",
        paragraphs: [
          "Processing times depend on workload, input size, system availability, and your plan. Any estimates shown in the product are indicative and not guaranteed. If a job fails due to a technical error on our side, contact support and we will work to restore service or address the issue consistent with our Refund Policy.",
        ],
      },
      {
        heading: "No physical shipping",
        paragraphs: [
          "Unless we expressly sell a physical item in a separate listing, nothing is mailed or couriered. This policy satisfies disclosure requirements for digital goods and services sold online in India.",
        ],
      },
    ],
  },
  contact: {
    title: "Contact Us",
    shortLabel: "Contact",
    sections: [
      {
        paragraphs: [
          "We are here to help with account access, billing, technical issues, and questions about these policies.",
        ],
      },
      {
        heading: "Correspondence address",
        paragraphs: [contactAddressBlock],
      },
      {
        heading: "Email (primary support channel)",
        paragraphs: [
          `Support: ${LEGAL_CONTACT_EMAIL}`,
          "We aim to acknowledge support emails within two (2) business days (Monday–Friday, excluding public holidays in India). Complex issues may require additional time; we will keep you informed.",
        ],
      },
      {
        heading: "What to include",
        paragraphs: [
          "For billing or refund requests, include your registered email, approximate date of payment, and any transaction or invoice reference shown in your receipt or bank/UPI statement. This helps us locate your payment quickly.",
        ],
      },
    ],
  },
  refunds: {
    title: "Cancellation and Refund Policy",
    shortLabel: "Refunds",
    sections: [
      {
        paragraphs: [
          "This Cancellation and Refund Policy applies to purchases and subscriptions for FlowLens made through our authorized checkout (including payments processed via Razorpay). It is published so you can understand how to cancel, when refunds may be available, and how to contact us before raising a dispute with your bank.",
          "Nothing in this policy limits statutory rights that cannot be waived under the Consumer Protection Act, 2019 or other applicable law in India.",
        ],
      },
      {
        heading: "Cancellation of subscriptions",
        paragraphs: [
          "Where recurring subscriptions are offered, you may cancel renewal through the billing or account controls described in the product, or by emailing us at the address below before the renewal date. Cancellation stops future charges; it does not automatically delete your account unless you request account closure.",
          "If you cancel, you typically retain access until the end of the current paid period unless we state otherwise at purchase or we terminate for cause.",
        ],
      },
      {
        heading: "Refund eligibility",
        paragraphs: [
          "We want fair outcomes. Refunds may be considered in situations including: (a) duplicate charges or accidental duplicate payments for the same order; (b) a technical failure on our side that prevented delivery of paid entitlements after reasonable troubleshooting; (c) charges made without your authorization (subject to verification); (d) where mandatory consumer law requires a remedy.",
          "For change-of-mind or subjective dissatisfaction with digital services, we review requests in good faith. Because digital access may be consumed immediately, refunds are not guaranteed in every case, but we will explain our decision and any alternatives (such as account credit) where applicable.",
        ],
      },
      {
        heading: "How to request a refund or cancellation assistance",
        paragraphs: [
          `Email ${LEGAL_CONTACT_EMAIL} with the subject line “Refund request” or “Cancellation help”, your registered email, order or invoice details, date and amount paid, and a short description of the issue.`,
          "Please contact us before initiating a chargeback or payment dispute with your bank or card issuer. Chargebacks can lead to account suspension while records are reviewed; most issues are resolved faster by working with us directly.",
        ],
      },
      {
        heading: "Processing time and method",
        paragraphs: [
          "Approved refunds are initiated to the original payment method where technically possible. Depending on your bank, card network, or UPI provider, refunded amounts may take approximately seven (7) to fourteen (14) business days to appear after we approve and process the refund. Weekends and bank holidays may extend this timeline.",
          "If the original method cannot receive a refund, we will propose a reasonable alternative (such as bank transfer) after identity and ownership checks.",
        ],
      },
      {
        heading: "Partial refunds and credits",
        paragraphs: [
          "In some cases we may offer a partial refund or account credit instead of a full refund, for example when partial use of a period has occurred or when a promotional price applied. We will describe the basis for any partial remedy.",
        ],
      },
      {
        heading: "Chargebacks and payment disputes",
        paragraphs: [
          "If you open a dispute with Razorpay or your bank, we will provide transaction and delivery records as appropriate. We reserve the right to limit or close accounts where we find repeated abusive dispute patterns or fraud.",
        ],
      },
      {
        heading: "Contact",
        paragraphs: [
          `Refunds and cancellation: ${LEGAL_CONTACT_EMAIL}`,
          "Correspondence address:",
          contactAddressBlock,
        ],
      },
    ],
  },
};

export function isLegalSlug(value: string): value is LegalSlug {
  return (LEGAL_SLUGS as readonly string[]).includes(value);
}
