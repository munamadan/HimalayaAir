interface ErrorPanelProps {
  message: string;
  onRetry: () => void;
}

export function ErrorPanel({ message, onRetry }: ErrorPanelProps) {
  return (
    <section className="error-panel" role="alert">
      <div>
        <span className="eyebrow">Update status</span>
        <strong>Some air-quality data is incomplete</strong>
        <p>{message}</p>
      </div>
      <button type="button" className="button button--secondary" onClick={onRetry}>
        Retry
      </button>
    </section>
  );
}
