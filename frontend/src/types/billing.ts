export type BillingProductPublic = {
  id: string;
  sku: string;
  kind: string;
  title: string;
  creditsLifetimeBonus: number;
  creditsDailyBonus: number;
  amountMinor: number;
  currency: string;
  stripeCheckoutMode: string;
  availableProviders: ("stripe" | "razorpay")[];
};

export type BillingProductAdmin = {
  id: string;
  sku: string;
  kind: string;
  title: string;
  creditsLifetimeBonus: number;
  creditsDailyBonus: number;
  amountMinor: number;
  currency: string;
  stripePriceId: string | null;
  stripeCheckoutMode: string;
  razorpayPlanId: string | null;
  active: boolean;
  extraJson: string;
};

export type PaymentPublicConfig = {
  razorpayKeyId: string | null;
  stripePublishableKey: string | null;
  billingGstInvoiceEnabled: boolean;
};

export type BillingInvoiceSummary = {
  id: string;
  invoiceNumber: string;
  issuedAt: string;
  currency: string;
  amountMinor: number;
  taxableAmountMinor: number;
  cgstMinor: number;
  sgstMinor: number;
  igstMinor: number;
  status: string;
  provider: string;
};

export type BillingRefundSummary = {
  id: string;
  userId: string | null;
  provider: string;
  providerRefundId: string;
  providerPaymentId: string | null;
  amountMinor: number;
  currency: string;
  status: string;
  initiatedBy: string;
  createdAt: string;
};

export type BillingDisputeSummary = {
  id: string;
  userId: string | null;
  provider: string;
  providerDisputeId: string;
  providerPaymentId: string | null;
  amountMinor: number | null;
  currency: string | null;
  status: string;
  reasonCode: string | null;
  openedAt: string | null;
  closedAt: string | null;
  createdAt: string;
};
