/**
 * Admin: GST invoices, refunds, chargebacks, initiate refund.
 */

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { paymentService } from "../../services/paymentService";
import { useToast } from "../../providers/ToastProvider";

export function BillingComplianceTab(): React.JSX.Element {
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const invoicesQuery = useQuery({
    queryKey: ["admin", "billing", "invoices"],
    queryFn: () => paymentService.adminListInvoices(),
  });
  const refundsQuery = useQuery({
    queryKey: ["admin", "billing", "refunds"],
    queryFn: () => paymentService.adminListRefunds(),
  });
  const disputesQuery = useQuery({
    queryKey: ["admin", "billing", "disputes"],
    queryFn: () => paymentService.adminListDisputes(),
  });

  const [provider, setProvider] = useState<"stripe" | "razorpay">("razorpay");
  const [paymentId, setPaymentId] = useState("");
  const [amountMinor, setAmountMinor] = useState("");

  const refundMutation = useMutation({
    mutationFn: () =>
      paymentService.adminInitiateRefund({
        provider,
        providerPaymentId: paymentId.trim(),
        amountMinor: amountMinor.trim() ? Number.parseInt(amountMinor, 10) : undefined,
      }),
    onSuccess: async () => {
      setPaymentId("");
      setAmountMinor("");
      await queryClient.invalidateQueries({ queryKey: ["admin", "billing", "refunds"] });
      showToast("info", "Refund request sent to provider.");
    },
    onError: (error: unknown) => {
      showToast("error", error instanceof Error ? error.message : "Refund failed.");
    },
  });

  return (
    <section className="panel stack admin-tab-panel" id="admin-panel-compliance" role="tabpanel" aria-labelledby="admin-tab-compliance">
      <div className="section-header-inline">
        <div>
          <h2>Compliance & finance</h2>
          <p className="muted">
            GST invoices (when enabled server-side), provider refunds, and Stripe disputes / Razorpay refund events.
          </p>
        </div>
      </div>

      <div className="panel stack">
        <h3>Initiate refund (admin)</h3>
        <p className="artifact-meta">
          Stripe: use PaymentIntent id (pi_…). Razorpay: use payment id (pay_…). Leave amount empty for full refund where
          supported.
        </p>
        <div className="admin-filter-bar" style={{ flexWrap: "wrap", alignItems: "flex-end" }}>
          <label className="admin-filter-field">
            <span>Provider</span>
            <select value={provider} onChange={(e) => setProvider(e.target.value as "stripe" | "razorpay")}>
              <option value="razorpay">razorpay</option>
              <option value="stripe">stripe</option>
            </select>
          </label>
          <label className="admin-filter-field" style={{ minWidth: "240px" }}>
            <span>Provider payment id</span>
            <input className="input-compact" value={paymentId} onChange={(e) => setPaymentId(e.target.value)} />
          </label>
          <label className="admin-filter-field">
            <span>Amount (minor, optional)</span>
            <input
              className="input-compact"
              value={amountMinor}
              onChange={(e) => setAmountMinor(e.target.value)}
              placeholder="full"
            />
          </label>
          <button
            type="button"
            className="button-primary"
            disabled={refundMutation.isPending || !paymentId.trim()}
            onClick={() => void refundMutation.mutateAsync()}
          >
            {refundMutation.isPending ? "Submitting…" : "Refund"}
          </button>
        </div>
      </div>

      <div className="panel stack">
        <h3>Invoices</h3>
        {invoicesQuery.isLoading ? <div className="empty-state">Loading…</div> : null}
        {invoicesQuery.data && invoicesQuery.data.length === 0 ? <div className="empty-state">No invoices yet.</div> : null}
        {invoicesQuery.data && invoicesQuery.data.length > 0 ? (
          <div className="admin-metrics-scroll">
            <table className="admin-metrics-table">
              <thead>
                <tr>
                  <th>Number</th>
                  <th>Issued</th>
                  <th>Amount</th>
                  <th>GST (taxable)</th>
                  <th>Status</th>
                  <th>Provider</th>
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
                    <td>{inv.taxableAmountMinor}</td>
                    <td>{inv.status}</td>
                    <td>{inv.provider}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>

      <div className="panel stack">
        <h3>Refunds</h3>
        {refundsQuery.data && refundsQuery.data.length > 0 ? (
          <div className="admin-metrics-scroll">
            <table className="admin-metrics-table">
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Refund id</th>
                  <th>Payment</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>By</th>
                </tr>
              </thead>
              <tbody>
                {refundsQuery.data.map((r) => (
                  <tr key={r.id}>
                    <td>{r.provider}</td>
                    <td className="artifact-meta">{r.providerRefundId}</td>
                    <td className="artifact-meta">{r.providerPaymentId ?? "—"}</td>
                    <td>
                      {r.amountMinor} {r.currency}
                    </td>
                    <td>{r.status}</td>
                    <td>{r.initiatedBy}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">{refundsQuery.isLoading ? "Loading…" : "No refunds recorded."}</div>
        )}
      </div>

      <div className="panel stack">
        <h3>Disputes / chargebacks</h3>
        {disputesQuery.data && disputesQuery.data.length > 0 ? (
          <div className="admin-metrics-scroll">
            <table className="admin-metrics-table">
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Dispute id</th>
                  <th>Payment</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {disputesQuery.data.map((d) => (
                  <tr key={d.id}>
                    <td>{d.provider}</td>
                    <td className="artifact-meta">{d.providerDisputeId}</td>
                    <td className="artifact-meta">{d.providerPaymentId ?? "—"}</td>
                    <td>
                      {d.amountMinor ?? "—"} {d.currency ?? ""}
                    </td>
                    <td>{d.status}</td>
                    <td className="artifact-meta">{d.reasonCode ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">{disputesQuery.isLoading ? "Loading…" : "No disputes recorded."}</div>
        )}
      </div>
    </section>
  );
}
