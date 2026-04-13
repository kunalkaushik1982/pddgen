/**
 * Mandatory policy links (e.g. Razorpay merchant requirements) on auth screens.
 */

import React from "react";
import { Link } from "react-router-dom";

const LINKS: { to: string; label: string }[] = [
  { to: "/legal/terms", label: "Terms and Conditions" },
  { to: "/legal/privacy", label: "Privacy Policy" },
  { to: "/legal/shipping", label: "Shipping Policy" },
  { to: "/legal/contact", label: "Contact Us" },
  { to: "/legal/refunds", label: "Cancellation and Refunds" },
];

export function AuthLegalFooter(): React.JSX.Element {
  return (
    <nav className="auth-legal-footer" aria-label="Legal and policies">
      <p className="auth-legal-footer-intro muted">Legal information</p>
      <ul className="auth-legal-footer-links">
        {LINKS.map((item) => (
          <li key={item.to}>
            <Link to={item.to} className="auth-legal-footer-link">
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
