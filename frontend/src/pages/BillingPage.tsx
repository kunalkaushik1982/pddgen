/**
 * Billing: catalog checkout with Razorpay (orders) or Stripe (redirect).
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import type { BillingProductPublic } from "../types/billing";
import { paymentService } from "../services/paymentService";
import { useAuth } from "../providers/AuthProvider";
import { useToast } from "../providers/ToastProvider";

function loadRazorpayScript(): Promise<void> {
  if (typeof window !== "undefined" && (window as unknown as { Razorpay?: unknown }).Razorpay) {
    return Promise.resolve();
  }
  return new Promise((resolve, reject) => {
    const existing = document.querySelector('script[data-razorpay-checkout="1"]');
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("Razorpay script failed")));
      return;
    }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.dataset.razorpayCheckout = "1";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Razorpay checkout script"));
    document.body.appendChild(script);
  });
}

export function BillingPage(): React.JSX.Element {
  const { showToast } = useToast();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const paid = searchParams.get("paid");

  const configQuery = useQuery({
    queryKey: ["payments", "public-config"],
    queryFn: () => paymentService.getPublicConfig(),
  });
  const productsQuery = useQuery({
    queryKey: ["payments", "products"],
    queryFn: () => paymentService.listProducts(),
  });
  const invoicesQuery = useQuery({
    queryKey: ["payments", "invoices"],
    queryFn: () => paymentService.listMyInvoices(),
  });

  const [busySku, setBusySku] = useState<string | null>(null);
  const [gstinDraft, setGstinDraft] = useState("");
  const [legalDraft, setLegalDraft] = useState("");
  const [stateDraft, setStateDraft] = useState("");

  useEffect(() => {
    if (!user) {
      return;
    }
    setGstinDraft(user.billingGstin ?? "");
    setLegalDraft(user.billingLegalName ?? "");
    setStateDraft(user.billingStateCode ?? "");
  }, [user]);

  const profileMutation = useMutation({
    mutationFn: () =>
      paymentService.patchBillingProfile({
        billingGstin: gstinDraft.trim() || null,
        billingLegalName: legalDraft.trim() || null,
        billingStateCode: stateDraft.trim() || null,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["auth", "currentUser"] });
      showToast("info", "Billing profile saved.");
    },
    onError: (error: unknown) => {
      showToast("error", error instanceof Error ? error.message : "Could not save profile.");
    },
  });

  const origin = useMemo(() => window.location.origin.replace(/\/+$/, ""), []);

  const pay = useCallback(
    async (product: BillingProductPublic, provider: "stripe" | "razorpay") => {
      setBusySku(product.sku);
      try {
        const successUrl = `${origin}/billing?paid=1`;
        const cancelUrl = `${origin}/billing?cancel=1`;
        const result = await paymentService.checkout({
          provider,
          productSku: product.sku,
          successUrl,
          cancelUrl,
          title: product.title,
        });

        if (provider === "stripe" && result.redirectUrl) {
          window.location.href = result.redirectUrl;
          return;
        }

        if (provider === "razorpay" && result.redirectUrl) {
          window.location.href = result.redirectUrl;
          return;
        }

        if (provider === "razorpay") {
          const key =
            (result.clientPayload.key_id as string | undefined) ?? configQuery.data?.razorpayKeyId ?? undefined;
          const orderId = result.clientPayload.order_id as string | undefined;
          const amount = result.clientPayload.amount as number | undefined;
          const currency = (result.clientPayload.currency as string | undefined) ?? product.currency;
          if (!key || !orderId || amount == null) {
            showToast(
              "error",
              "Razorpay checkout is missing key or order details. Check server keys and product amount.",
            );
            return;
          }
          await loadRazorpayScript();
          const RazorpayCtor = (window as unknown as { Razorpay: new (opts: Record<string, unknown>) => { open: () => void } })
            .Razorpay;
          const rzp = new RazorpayCtor({
            key,
            amount,
            currency,
            order_id: orderId,
            name: "PDD Generator",
            description: product.title,
            handler() {
              showToast("info", "Payment submitted. Credits apply when the webhook confirms.");
            },
          });
          rzp.open();
        }
      } catch (error: unknown) {
        const text = error instanceof Error ? error.message : "Checkout failed.";
        showToast("error", text);
      } finally {
        setBusySku(null);
      }
    },
    [configQuery.data?.razorpayKeyId, origin, showToast],
  );

  return (
    <div className="stack">
      <section className="panel stack">
        <h3>Invoice & GST details (optional)</h3>
        <p className="muted">
          Used on tax invoices when your administrator enables GST invoicing on the server. Two-letter state code for
          place of supply (e.g. KA).
        </p>
        {configQuery.data?.billingGstInvoiceEnabled ? (
          <div className="status-toast status-toast-info" role="status">
            GST invoicing is enabled: ensure your legal name and state match your records.
          </div>
        ) : null}
        <div className="admin-filter-bar" style={{ flexWrap: "wrap", alignItems: "flex-end" }}>
          <label className="admin-filter-field">
            <span>Legal name</span>
            <input className="input-compact" value={legalDraft} onChange={(e) => setLegalDraft(e.target.value)} />
          </label>
          <label className="admin-filter-field">
            <span>GSTIN</span>
            <input className="input-compact" value={gstinDraft} onChange={(e) => setGstinDraft(e.target.value)} />
          </label>
          <label className="admin-filter-field">
            <span>State code</span>
            <input
              className="input-compact"
              maxLength={2}
              value={stateDraft}
              onChange={(e) => setStateDraft(e.target.value.toUpperCase())}
            />
          </label>
          <button
            type="button"
            className="button-secondary"
            disabled={profileMutation.isPending}
            onClick={() => void profileMutation.mutateAsync()}
          >
            {profileMutation.isPending ? "Saving…" : "Save"}
          </button>
        </div>
      </section>

      <section className="panel stack">
        <h3>Your invoices</h3>
        {invoicesQuery.isLoading ? <div className="empty-state">Loading invoices…</div> : null}
        {invoicesQuery.data && invoicesQuery.data.length === 0 ? (
          <div className="empty-state">No invoices yet. They appear after successful payments when invoicing is enabled.</div>
        ) : null}
        {invoicesQuery.data && invoicesQuery.data.length > 0 ? (
          <div className="admin-metrics-scroll">
            <table className="admin-metrics-table">
              <thead>
                <tr>
                  <th>Number</th>
                  <th>Issued</th>
                  <th>Total</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {invoicesQuery.data.map((inv) => (
                  <tr key={inv.id}>
                    <td>{inv.invoiceNumber}</td>
                    <td className="artifact-meta">{new Date(inv.issuedAt).toLocaleString()}</td>
                    <td>
                      {inv.amountMinor} {inv.currency}
                    </td>
                    <td>{inv.status}</td>
                    <td>
                      <button
                        type="button"
                        className="button-secondary"
                        onClick={() =>
                          void paymentService.downloadInvoiceDocument(inv.id, `invoice-${inv.invoiceNumber}.txt`)
                        }
                      >
                        Download
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="panel stack">
        <h2>Billing & credits</h2>
        <p className="muted">
          Purchase credit packs or subscriptions configured by your administrator. Razorpay opens in-page for one-time
          orders; subscriptions may redirect to Razorpay or Stripe depending on the product.
        </p>
        {paid === "1" ? (
          <div className="status-toast status-toast-info" role="status">
            Payment completed. If credits did not update within a minute, contact support with your session time.
          </div>
        ) : null}
        {searchParams.get("cancel") === "1" ? (
          <div className="status-toast status-toast-info" role="status">
            Checkout cancelled.
          </div>
        ) : null}
        {productsQuery.isLoading ? <div className="empty-state">Loading products…</div> : null}
        {productsQuery.error ? (
          <div className="empty-state">Could not load products. Ensure you are signed in and the API is reachable.</div>
        ) : null}
        {productsQuery.data && productsQuery.data.length === 0 ? (
          <div className="empty-state">No active billing products yet. Ask an admin to add catalog rows.</div>
        ) : null}
        <div className="button-row" style={{ flexWrap: "wrap", gap: "12px" }}>
          {productsQuery.data?.map((product) => (
            <div key={product.id} className="panel stack" style={{ minWidth: "240px", flex: "1 1 240px" }}>
              <strong>{product.title}</strong>
              <div className="artifact-meta">{product.sku}</div>
              <div className="artifact-meta">
                {product.kind} · {product.amountMinor / 100} {product.currency} (display) · +{product.creditsLifetimeBonus}{" "}
                lifetime bonus steps
              </div>
              <div className="artifact-meta">Providers: {product.availableProviders.join(", ")}</div>
              {product.availableProviders.includes("razorpay") ? (
                <button
                  type="button"
                  className="button-primary"
                  disabled={busySku !== null}
                  onClick={() => void pay(product, "razorpay")}
                >
                  {busySku === product.sku ? "Starting…" : "Pay with Razorpay"}
                </button>
              ) : null}
              {!configQuery.data?.razorpayKeyId && product.availableProviders.includes("razorpay") ? (
                <div className="artifact-meta">
                  Public key not exposed until checkout; ensure Razorpay keys are set on the server.
                </div>
              ) : null}
              {product.availableProviders.includes("stripe") ? (
                <button
                  type="button"
                  className="button-secondary"
                  disabled={busySku !== null}
                  onClick={() => void pay(product, "stripe")}
                >
                  {busySku === product.sku ? "Starting…" : "Pay with Stripe"}
                </button>
              ) : null}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
