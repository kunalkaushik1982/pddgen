import type {
  BillingDisputeSummary,
  BillingInvoiceSummary,
  BillingProductAdmin,
  BillingProductPublic,
  BillingRefundSummary,
  PaymentPublicConfig,
} from "../types/billing";
import { API_BASE_URL, fetchJson } from "./http";

type BackendBillingProductPublic = {
  id: string;
  sku: string;
  kind: string;
  title: string;
  credits_lifetime_bonus: number;
  credits_daily_bonus: number;
  amount_minor: number;
  currency: string;
  stripe_checkout_mode: string;
  available_providers: ("stripe" | "razorpay")[];
};

type BackendBillingProductAdmin = {
  id: string;
  sku: string;
  kind: string;
  title: string;
  credits_lifetime_bonus: number;
  credits_daily_bonus: number;
  amount_minor: number;
  currency: string;
  stripe_price_id: string | null;
  stripe_checkout_mode: string;
  razorpay_plan_id: string | null;
  active: boolean;
  extra_json: string;
};

function mapPublic(row: BackendBillingProductPublic): BillingProductPublic {
  return {
    id: row.id,
    sku: row.sku,
    kind: row.kind,
    title: row.title,
    creditsLifetimeBonus: row.credits_lifetime_bonus,
    creditsDailyBonus: row.credits_daily_bonus,
    amountMinor: row.amount_minor,
    currency: row.currency,
    stripeCheckoutMode: row.stripe_checkout_mode,
    availableProviders: row.available_providers,
  };
}

function mapAdmin(row: BackendBillingProductAdmin): BillingProductAdmin {
  return {
    id: row.id,
    sku: row.sku,
    kind: row.kind,
    title: row.title,
    creditsLifetimeBonus: row.credits_lifetime_bonus,
    creditsDailyBonus: row.credits_daily_bonus,
    amountMinor: row.amount_minor,
    currency: row.currency,
    stripePriceId: row.stripe_price_id,
    stripeCheckoutMode: row.stripe_checkout_mode,
    razorpayPlanId: row.razorpay_plan_id,
    active: row.active,
    extraJson: row.extra_json,
  };
}

export type PaymentCheckoutPayload = {
  provider: "stripe" | "razorpay";
  productSku?: string;
  amountMinor?: number;
  currency?: string;
  successUrl: string;
  cancelUrl: string;
  title?: string;
  metadata?: Record<string, string>;
};

type BackendCheckoutResponse = {
  provider: string;
  provider_session_id: string;
  redirect_url: string | null;
  client_payload: Record<string, unknown>;
};

export type PaymentCheckoutResult = {
  provider: string;
  providerSessionId: string;
  redirectUrl: string | null;
  clientPayload: Record<string, unknown>;
};

export const paymentService = {
  async getPublicConfig(): Promise<PaymentPublicConfig> {
    const row = await fetchJson<{
      razorpay_key_id: string | null;
      stripe_publishable_key: string | null;
      billing_gst_invoice_enabled?: boolean;
    }>("/payments/public-config");
    return {
      razorpayKeyId: row.razorpay_key_id,
      stripePublishableKey: row.stripe_publishable_key,
      billingGstInvoiceEnabled: Boolean(row.billing_gst_invoice_enabled),
    };
  },

  async listProducts(): Promise<BillingProductPublic[]> {
    const rows = await fetchJson<BackendBillingProductPublic[]>("/payments/products");
    return rows.map(mapPublic);
  },

  async checkout(body: PaymentCheckoutPayload): Promise<PaymentCheckoutResult> {
    const payload: Record<string, unknown> = {
      provider: body.provider,
      success_url: body.successUrl,
      cancel_url: body.cancelUrl,
      title: body.title ?? "Payment",
      metadata: body.metadata ?? {},
    };
    if (body.productSku) {
      payload.product_sku = body.productSku;
    } else {
      payload.amount_minor = body.amountMinor;
      payload.currency = body.currency;
    }
    const row = await fetchJson<BackendCheckoutResponse>("/payments/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return {
      provider: row.provider,
      providerSessionId: row.provider_session_id,
      redirectUrl: row.redirect_url,
      clientPayload: row.client_payload,
    };
  },

  async adminListProducts(): Promise<BillingProductAdmin[]> {
    const rows = await fetchJson<BackendBillingProductAdmin[]>("/admin/billing/products");
    return rows.map(mapAdmin);
  },

  async adminCreateProduct(payload: {
    sku: string;
    kind: string;
    title: string;
    creditsLifetimeBonus: number;
    creditsDailyBonus: number;
    amountMinor: number;
    currency: string;
    stripePriceId?: string | null;
    stripeCheckoutMode?: string;
    razorpayPlanId?: string | null;
    active?: boolean;
    extraJson?: string;
  }): Promise<BillingProductAdmin> {
    const row = await fetchJson<BackendBillingProductAdmin>("/admin/billing/products", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sku: payload.sku,
        kind: payload.kind,
        title: payload.title,
        credits_lifetime_bonus: payload.creditsLifetimeBonus,
        credits_daily_bonus: payload.creditsDailyBonus,
        amount_minor: payload.amountMinor,
        currency: payload.currency,
        stripe_price_id: payload.stripePriceId ?? null,
        stripe_checkout_mode: payload.stripeCheckoutMode ?? "payment",
        razorpay_plan_id: payload.razorpayPlanId ?? null,
        active: payload.active ?? true,
        extra_json: payload.extraJson ?? "{}",
      }),
    });
    return mapAdmin(row);
  },

  async adminUpdateProduct(
    productId: string,
    payload: Partial<{
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
    }>,
  ): Promise<BillingProductAdmin> {
    const body: Record<string, unknown> = {};
    if (payload.kind !== undefined) body.kind = payload.kind;
    if (payload.title !== undefined) body.title = payload.title;
    if (payload.creditsLifetimeBonus !== undefined) body.credits_lifetime_bonus = payload.creditsLifetimeBonus;
    if (payload.creditsDailyBonus !== undefined) body.credits_daily_bonus = payload.creditsDailyBonus;
    if (payload.amountMinor !== undefined) body.amount_minor = payload.amountMinor;
    if (payload.currency !== undefined) body.currency = payload.currency;
    if (payload.stripePriceId !== undefined) body.stripe_price_id = payload.stripePriceId;
    if (payload.stripeCheckoutMode !== undefined) body.stripe_checkout_mode = payload.stripeCheckoutMode;
    if (payload.razorpayPlanId !== undefined) body.razorpay_plan_id = payload.razorpayPlanId;
    if (payload.active !== undefined) body.active = payload.active;
    if (payload.extraJson !== undefined) body.extra_json = payload.extraJson;
    const row = await fetchJson<BackendBillingProductAdmin>(`/admin/billing/products/${encodeURIComponent(productId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return mapAdmin(row);
  },

  async adminDeleteProduct(productId: string): Promise<void> {
    await fetchJson<undefined>(`/admin/billing/products/${encodeURIComponent(productId)}`, {
      method: "DELETE",
    });
  },

  async patchBillingProfile(payload: {
    billingGstin?: string | null;
    billingLegalName?: string | null;
    billingStateCode?: string | null;
  }): Promise<void> {
    await fetchJson<undefined>("/payments/billing-profile", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        billing_gstin: payload.billingGstin ?? null,
        billing_legal_name: payload.billingLegalName ?? null,
        billing_state_code: payload.billingStateCode ?? null,
      }),
    });
  },

  async listMyInvoices(): Promise<BillingInvoiceSummary[]> {
    type Row = {
      id: string;
      invoice_number: string;
      issued_at: string;
      currency: string;
      amount_minor: number;
      taxable_amount_minor: number;
      cgst_minor: number;
      sgst_minor: number;
      igst_minor: number;
      status: string;
      provider: string;
    };
    const rows = await fetchJson<Row[]>("/payments/invoices");
    return rows.map((row) => ({
      id: row.id,
      invoiceNumber: row.invoice_number,
      issuedAt: row.issued_at,
      currency: row.currency,
      amountMinor: row.amount_minor,
      taxableAmountMinor: row.taxable_amount_minor,
      cgstMinor: row.cgst_minor,
      sgstMinor: row.sgst_minor,
      igstMinor: row.igst_minor,
      status: row.status,
      provider: row.provider,
    }));
  },

  async downloadInvoiceDocument(invoiceId: string, filename: string): Promise<void> {
    const response = await fetch(
      `${API_BASE_URL}/payments/invoices/${encodeURIComponent(invoiceId)}/document`,
      { credentials: "include" },
    );
    if (!response.ok) {
      throw new Error(`Download failed (${response.status})`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  },

  async adminListInvoices(): Promise<BillingInvoiceSummary[]> {
    type Row = {
      id: string;
      invoice_number: string;
      issued_at: string;
      currency: string;
      amount_minor: number;
      taxable_amount_minor: number;
      cgst_minor: number;
      sgst_minor: number;
      igst_minor: number;
      status: string;
      provider: string;
    };
    const rows = await fetchJson<Row[]>("/admin/billing/invoices");
    return rows.map((row) => ({
      id: row.id,
      invoiceNumber: row.invoice_number,
      issuedAt: row.issued_at,
      currency: row.currency,
      amountMinor: row.amount_minor,
      taxableAmountMinor: row.taxable_amount_minor,
      cgstMinor: row.cgst_minor,
      sgstMinor: row.sgst_minor,
      igstMinor: row.igst_minor,
      status: row.status,
      provider: row.provider,
    }));
  },

  async adminListRefunds(): Promise<BillingRefundSummary[]> {
    type Row = {
      id: string;
      user_id: string | null;
      provider: string;
      provider_refund_id: string;
      provider_payment_id: string | null;
      amount_minor: number;
      currency: string;
      status: string;
      initiated_by: string;
      created_at: string;
    };
    const rows = await fetchJson<Row[]>("/admin/billing/refunds");
    return rows.map((row) => ({
      id: row.id,
      userId: row.user_id,
      provider: row.provider,
      providerRefundId: row.provider_refund_id,
      providerPaymentId: row.provider_payment_id,
      amountMinor: row.amount_minor,
      currency: row.currency,
      status: row.status,
      initiatedBy: row.initiated_by,
      createdAt: row.created_at,
    }));
  },

  async adminListDisputes(): Promise<BillingDisputeSummary[]> {
    type Row = {
      id: string;
      user_id: string | null;
      provider: string;
      provider_dispute_id: string;
      provider_payment_id: string | null;
      amount_minor: number | null;
      currency: string | null;
      status: string;
      reason_code: string | null;
      opened_at: string | null;
      closed_at: string | null;
      created_at: string;
    };
    const rows = await fetchJson<Row[]>("/admin/billing/disputes");
    return rows.map((row) => ({
      id: row.id,
      userId: row.user_id,
      provider: row.provider,
      providerDisputeId: row.provider_dispute_id,
      providerPaymentId: row.provider_payment_id,
      amountMinor: row.amount_minor,
      currency: row.currency,
      status: row.status,
      reasonCode: row.reason_code,
      openedAt: row.opened_at,
      closedAt: row.closed_at,
      createdAt: row.created_at,
    }));
  },

  async adminInitiateRefund(payload: {
    provider: "stripe" | "razorpay";
    providerPaymentId: string;
    amountMinor?: number;
    notes?: string;
  }): Promise<{ ok: boolean; providerRefundId: string | null; raw: unknown }> {
    const row = await fetchJson<{ ok: boolean; provider_refund_id: string | null; raw: unknown }>(
      "/admin/billing/refunds/initiate",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: payload.provider,
          provider_payment_id: payload.providerPaymentId,
          amount_minor: payload.amountMinor,
          notes: payload.notes,
        }),
      },
    );
    return { ok: row.ok, providerRefundId: row.provider_refund_id, raw: row.raw };
  },
};
