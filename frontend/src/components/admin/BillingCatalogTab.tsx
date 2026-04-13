/**
 * Admin: create and manage billing catalog rows (Stripe + Razorpay).
 */

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { paymentService } from "../../services/paymentService";
import type { BillingProductAdmin } from "../../types/billing";
import { useToast } from "../../providers/ToastProvider";

const emptyCreate = {
  sku: "",
  kind: "CREDIT_PACK",
  title: "",
  creditsLifetimeBonus: 0,
  creditsDailyBonus: 0,
  amountMinor: 0,
  currency: "INR",
  stripePriceId: "" as string | null,
  stripeCheckoutMode: "payment",
  razorpayPlanId: "" as string | null,
  extraJson: "{}",
};

export function BillingCatalogTab(): React.JSX.Element {
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [createDraft, setCreateDraft] = useState(emptyCreate);
  const [editing, setEditing] = useState<BillingProductAdmin | null>(null);

  const listQuery = useQuery({
    queryKey: ["admin", "billing", "products"],
    queryFn: () => paymentService.adminListProducts(),
  });

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: ["admin", "billing", "products"] });
    await queryClient.invalidateQueries({ queryKey: ["payments", "products"] });
  };

  const createMutation = useMutation({
    mutationFn: () =>
      paymentService.adminCreateProduct({
        sku: createDraft.sku.trim(),
        kind: createDraft.kind.trim(),
        title: createDraft.title.trim(),
        creditsLifetimeBonus: createDraft.creditsLifetimeBonus,
        creditsDailyBonus: createDraft.creditsDailyBonus,
        amountMinor: createDraft.amountMinor,
        currency: createDraft.currency.trim().toUpperCase(),
        stripePriceId: createDraft.stripePriceId?.trim() || null,
        stripeCheckoutMode: createDraft.stripeCheckoutMode,
        razorpayPlanId: createDraft.razorpayPlanId?.trim() || null,
        active: true,
        extraJson: createDraft.extraJson.trim() || "{}",
      }),
    onSuccess: async () => {
      setCreateDraft({ ...emptyCreate });
      await invalidate();
      showToast("info", "Product created.");
    },
    onError: (error: unknown) => {
      showToast("error", error instanceof Error ? error.message : "Create failed.");
    },
  });

  const patchMutation = useMutation({
    mutationFn: (payload: { id: string; body: Parameters<typeof paymentService.adminUpdateProduct>[1] }) =>
      paymentService.adminUpdateProduct(payload.id, payload.body),
    onSuccess: async () => {
      setEditing(null);
      await invalidate();
      showToast("info", "Product updated.");
    },
    onError: (error: unknown) => {
      showToast("error", error instanceof Error ? error.message : "Update failed.");
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: string) => paymentService.adminDeleteProduct(id),
    onSuccess: async () => {
      await invalidate();
      showToast("info", "Product deactivated.");
    },
    onError: (error: unknown) => {
      showToast("error", error instanceof Error ? error.message : "Deactivate failed.");
    },
  });

  return (
    <section className="panel stack admin-tab-panel" id="admin-panel-catalog" role="tabpanel" aria-labelledby="admin-tab-catalog">
      <div className="section-header-inline">
        <div>
          <h2>Billing catalog</h2>
          <p className="muted">
            Define SKUs, amounts (minor units: paise for INR, cents for USD), and provider ids. Razorpay one-time orders
            use amount; subscriptions need a Razorpay plan id. Stripe uses price ids.
          </p>
        </div>
      </div>

      <div className="panel stack">
        <h3>New product</h3>
        <div className="admin-filter-bar" style={{ flexWrap: "wrap", alignItems: "flex-end" }}>
          <label className="admin-filter-field">
            <span>SKU</span>
            <input
              className="input-compact"
              value={createDraft.sku}
              onChange={(e) => setCreateDraft((d) => ({ ...d, sku: e.target.value }))}
            />
          </label>
          <label className="admin-filter-field">
            <span>Kind</span>
            <input
              className="input-compact"
              value={createDraft.kind}
              onChange={(e) => setCreateDraft((d) => ({ ...d, kind: e.target.value }))}
            />
          </label>
          <label className="admin-filter-field" style={{ minWidth: "200px" }}>
            <span>Title</span>
            <input
              className="input-compact"
              value={createDraft.title}
              onChange={(e) => setCreateDraft((d) => ({ ...d, title: e.target.value }))}
            />
          </label>
          <label className="admin-filter-field">
            <span>Amount (minor)</span>
            <input
              type="number"
              className="input-compact"
              value={createDraft.amountMinor}
              onChange={(e) => setCreateDraft((d) => ({ ...d, amountMinor: Number.parseInt(e.target.value, 10) || 0 }))}
            />
          </label>
          <label className="admin-filter-field">
            <span>Currency</span>
            <input
              className="input-compact"
              maxLength={3}
              value={createDraft.currency}
              onChange={(e) => setCreateDraft((d) => ({ ...d, currency: e.target.value }))}
            />
          </label>
          <label className="admin-filter-field">
            <span>Lifetime bonus</span>
            <input
              type="number"
              className="input-compact"
              value={createDraft.creditsLifetimeBonus}
              onChange={(e) =>
                setCreateDraft((d) => ({ ...d, creditsLifetimeBonus: Number.parseInt(e.target.value, 10) || 0 }))
              }
            />
          </label>
          <label className="admin-filter-field">
            <span>Daily bonus</span>
            <input
              type="number"
              className="input-compact"
              value={createDraft.creditsDailyBonus}
              onChange={(e) =>
                setCreateDraft((d) => ({ ...d, creditsDailyBonus: Number.parseInt(e.target.value, 10) || 0 }))
              }
            />
          </label>
          <label className="admin-filter-field">
            <span>Stripe price id</span>
            <input
              className="input-compact"
              value={createDraft.stripePriceId ?? ""}
              onChange={(e) => setCreateDraft((d) => ({ ...d, stripePriceId: e.target.value || null }))}
            />
          </label>
          <label className="admin-filter-field">
            <span>Stripe mode</span>
            <select
              value={createDraft.stripeCheckoutMode}
              onChange={(e) => setCreateDraft((d) => ({ ...d, stripeCheckoutMode: e.target.value }))}
            >
              <option value="payment">payment</option>
              <option value="subscription">subscription</option>
            </select>
          </label>
          <label className="admin-filter-field">
            <span>Razorpay plan id</span>
            <input
              className="input-compact"
              value={createDraft.razorpayPlanId ?? ""}
              onChange={(e) => setCreateDraft((d) => ({ ...d, razorpayPlanId: e.target.value || null }))}
            />
          </label>
        </div>
        <label className="admin-filter-field" style={{ minWidth: "100%" }}>
          <span>extra_json</span>
          <textarea
            className="input-compact"
            rows={2}
            value={createDraft.extraJson}
            onChange={(e) => setCreateDraft((d) => ({ ...d, extraJson: e.target.value }))}
          />
        </label>
        <button
          type="button"
          className="button-primary"
          disabled={createMutation.isPending || !createDraft.sku.trim() || !createDraft.title.trim()}
          onClick={() => void createMutation.mutateAsync()}
        >
          {createMutation.isPending ? "Creating…" : "Create product"}
        </button>
      </div>

      {listQuery.isLoading ? <div className="empty-state">Loading catalog…</div> : null}
      {listQuery.error ? <div className="empty-state">Could not load catalog.</div> : null}

      {editing ? (
        <div className="panel stack">
          <h3>Edit {editing.sku}</h3>
          <div className="admin-filter-bar" style={{ flexWrap: "wrap", alignItems: "flex-end" }}>
            <label className="admin-filter-field" style={{ minWidth: "220px" }}>
              <span>Title</span>
              <input
                className="input-compact"
                value={editing.title}
                onChange={(e) => setEditing({ ...editing, title: e.target.value })}
              />
            </label>
            <label className="admin-filter-field">
              <span>Amount (minor)</span>
              <input
                type="number"
                className="input-compact"
                value={editing.amountMinor}
                onChange={(e) => setEditing({ ...editing, amountMinor: Number.parseInt(e.target.value, 10) || 0 })}
              />
            </label>
            <label className="admin-filter-field">
              <span>Currency</span>
              <input
                className="input-compact"
                maxLength={3}
                value={editing.currency}
                onChange={(e) => setEditing({ ...editing, currency: e.target.value.toUpperCase() })}
              />
            </label>
            <label className="admin-filter-field">
              <span>Lifetime bonus</span>
              <input
                type="number"
                className="input-compact"
                value={editing.creditsLifetimeBonus}
                onChange={(e) =>
                  setEditing({ ...editing, creditsLifetimeBonus: Number.parseInt(e.target.value, 10) || 0 })
                }
              />
            </label>
            <label className="admin-filter-field">
              <span>Daily bonus</span>
              <input
                type="number"
                className="input-compact"
                value={editing.creditsDailyBonus}
                onChange={(e) =>
                  setEditing({ ...editing, creditsDailyBonus: Number.parseInt(e.target.value, 10) || 0 })
                }
              />
            </label>
            <label className="admin-filter-field">
              <span>Stripe price id</span>
              <input
                className="input-compact"
                value={editing.stripePriceId ?? ""}
                onChange={(e) => setEditing({ ...editing, stripePriceId: e.target.value || null })}
              />
            </label>
            <label className="admin-filter-field">
              <span>Stripe mode</span>
              <select
                value={editing.stripeCheckoutMode}
                onChange={(e) => setEditing({ ...editing, stripeCheckoutMode: e.target.value })}
              >
                <option value="payment">payment</option>
                <option value="subscription">subscription</option>
              </select>
            </label>
            <label className="admin-filter-field">
              <span>Razorpay plan id</span>
              <input
                className="input-compact"
                value={editing.razorpayPlanId ?? ""}
                onChange={(e) => setEditing({ ...editing, razorpayPlanId: e.target.value || null })}
              />
            </label>
          </div>
          <label className="admin-filter-field" style={{ minWidth: "100%" }}>
            <span>extra_json</span>
            <textarea
              className="input-compact"
              rows={2}
              value={editing.extraJson}
              onChange={(e) => setEditing({ ...editing, extraJson: e.target.value })}
            />
          </label>
          <div className="button-row">
            <button
              type="button"
              className="button-primary"
              disabled={patchMutation.isPending}
              onClick={() =>
                void patchMutation.mutateAsync({
                  id: editing.id,
                  body: {
                    title: editing.title,
                    amountMinor: editing.amountMinor,
                    currency: editing.currency,
                    stripePriceId: editing.stripePriceId,
                    stripeCheckoutMode: editing.stripeCheckoutMode,
                    razorpayPlanId: editing.razorpayPlanId,
                    creditsLifetimeBonus: editing.creditsLifetimeBonus,
                    creditsDailyBonus: editing.creditsDailyBonus,
                    extraJson: editing.extraJson,
                  },
                })
              }
            >
              {patchMutation.isPending ? "Saving…" : "Save"}
            </button>
            <button type="button" className="button-secondary" onClick={() => setEditing(null)}>
              Cancel
            </button>
          </div>
        </div>
      ) : null}

      {listQuery.data && listQuery.data.length > 0 ? (
        <div className="admin-metrics-scroll">
          <table className="admin-metrics-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Title</th>
                <th>Kind</th>
                <th>Amount</th>
                <th>Active</th>
                <th>Stripe</th>
                <th>Razorpay plan</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {listQuery.data.map((row) => (
                <tr key={row.id}>
                  <td>{row.sku}</td>
                  <td>{row.title}</td>
                  <td>{row.kind}</td>
                  <td>{`${row.amountMinor} ${row.currency}`}</td>
                  <td>{row.active ? "yes" : "no"}</td>
                  <td className="artifact-meta">{row.stripePriceId ?? "—"}</td>
                  <td className="artifact-meta">{row.razorpayPlanId ?? "—"}</td>
                  <td>
                    <button type="button" className="button-secondary" onClick={() => setEditing({ ...row })}>
                      Edit
                    </button>{" "}
                    {row.active ? (
                      <button
                        type="button"
                        className="button-secondary"
                        disabled={deactivateMutation.isPending}
                        onClick={() => void deactivateMutation.mutateAsync(row.id)}
                      >
                        Deactivate
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
