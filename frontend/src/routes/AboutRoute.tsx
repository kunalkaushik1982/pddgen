import React from "react";
import { useQuery } from "@tanstack/react-query";

import { AboutPage } from "../pages/AboutPage";
import { aboutService } from "../services/aboutService";

export function AboutRoute(): React.JSX.Element {
  const aboutQuery = useQuery({
    queryKey: ["about"],
    queryFn: aboutService.getAbout,
    retry: false,
  });

  if (aboutQuery.isLoading) {
    return (
      <section className="panel">
        <div className="empty-state">Loading release metadata...</div>
      </section>
    );
  }

  if (aboutQuery.isError || !aboutQuery.data) {
    return (
      <section className="panel">
        <div className="empty-state">About information is not available right now.</div>
      </section>
    );
  }

  return <AboutPage about={aboutQuery.data} />;
}
