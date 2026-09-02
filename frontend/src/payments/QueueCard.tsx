import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

/** The shell every payments queue draws itself in: a heading, the count of what
 *  it holds, and its rows.
 *
 *  A queue with nothing in it renders its heading and a zero, and no body. The
 *  absence is stated rather than omitted — that is the console's idiom
 *  everywhere — but these four cards sit above the fencer table, not beside it
 *  in the rail, so a full "nothing here" card each would push the table down by
 *  four cards on the ordinary tournament where nothing is wrong (design
 *  add-payments-console-ui D1).
 *
 *  Loading and failure are the same shape: one line, the card's own, so one
 *  queue failing leaves the other three and the table as they were.
 */
export default function QueueCard({
  title,
  count,
  loading = false,
  failed = false,
  children,
}: {
  title: string;
  /** null while the count is not yet known — the heading shows no number
   *  rather than a zero it would have to take back. */
  count: number | null;
  loading?: boolean;
  failed?: boolean;
  children?: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <section className={`rail-card queue-card${count === 0 ? " queue-card-empty" : ""}`}>
      <div className="rail-card-heading">
        <h2>{title}</h2>
        {count !== null && <span className="rail-count">{count}</span>}
      </div>
      {failed ? (
        <p className="login-error">{t("payments.queue.failed")}</p>
      ) : loading ? (
        <p className="rail-hint">{t("common.loading")}</p>
      ) : (
        count !== 0 && children
      )}
    </section>
  );
}
