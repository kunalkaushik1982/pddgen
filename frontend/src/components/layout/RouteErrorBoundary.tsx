import React from "react";

type RouteErrorBoundaryProps = {
  areaLabel: string;
  children: React.ReactNode;
};

type RouteErrorBoundaryState = {
  hasError: boolean;
  errorMessage: string;
};

export class RouteErrorBoundary extends React.Component<RouteErrorBoundaryProps, RouteErrorBoundaryState> {
  public constructor(props: RouteErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      errorMessage: "",
    };
  }

  public static getDerivedStateFromError(error: unknown): RouteErrorBoundaryState {
    return {
      hasError: true,
      errorMessage: error instanceof Error ? error.message : "Unexpected application error.",
    };
  }

  public componentDidCatch(error: unknown): void {
    console.error("RouteErrorBoundary", this.props.areaLabel, error);
  }

  public render(): React.ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <section className="panel stack" role="alert" aria-live="assertive">
        <div>
          <h2>{this.props.areaLabel} Unavailable</h2>
          <p className="muted">This screen hit a rendering error. Refresh or navigate back to continue working.</p>
        </div>
        <div className="message-banner error">{this.state.errorMessage}</div>
      </section>
    );
  }
}
