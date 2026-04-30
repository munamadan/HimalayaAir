interface LoadingStateProps {
  title: string;
  detail?: string;
}

export function LoadingState({ title, detail }: LoadingStateProps) {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <span className="loading-state__ring" />
      <div>
        <strong>{title}</strong>
        {detail && <p>{detail}</p>}
      </div>
    </div>
  );
}
