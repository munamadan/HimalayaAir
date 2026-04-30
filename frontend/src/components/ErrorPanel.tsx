interface ErrorPanelProps {
  message: string;
  onRetry: () => void;
}

export function ErrorPanel({ message, onRetry }: ErrorPanelProps) {
  return (
    <section className="error-panel" role="alert">
      <div>
        <span className="eyebrow">API state</span>
        <strong>Dashboard data is incomplete</strong>
        <p>{message}</p>
      </div>
      <button type="button" className="button button--secondary" onClick={onRetry}>
        Retry API fetch
      </button>
    </section>
  );
}
