import { Clock, CalendarX2, Flame } from "lucide-react";

export default function DeadlineCountdown({ deadline }) {
  if (!deadline) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-ink-muted">
        <CalendarX2 className="h-3.5 w-3.5" /> No deadline
      </span>
    );
  }

  const days = Math.ceil((new Date(deadline) - new Date()) / 86400000);
  let cls = "text-ink-muted";
  let label = `${days} days left`;
  let Icon = Clock;

  if (days < 0) {
    cls = "text-ink-muted";
    label = "Closed";
    Icon = CalendarX2;
  } else if (days === 0) {
    cls = "text-red-600 font-semibold";
    label = "Due today";
    Icon = Flame;
  } else if (days <= 3) {
    cls = "text-red-500 font-semibold";
    Icon = Flame;
  } else if (days <= 7) {
    cls = "text-amber-600 font-medium";
  }

  return (
    <span className={`inline-flex items-center gap-1 text-xs ${cls}`} title={deadline}>
      <Icon className="h-3.5 w-3.5" strokeWidth={2.2} />
      {label}
    </span>
  );
}
