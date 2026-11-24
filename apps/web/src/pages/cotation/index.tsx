/** Cotation de la semaine — which butchers have been told this week's carcass price move (GET /api/cotation/board).
 *  The voice agent tells them during their call; the rest are for their salesperson. Live on cotation.* events. */
import { useCallback } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { BellRing, CheckCircle2, TrendingUp } from "lucide-react";
import type { ActivityEvent } from "@kit/shared";
import { API_BASE } from "@/lib/api";
import { useOnActivity } from "@/lib/queries";
import { Badge, Card, DateLabel, ErrorState, Page, PageBody, PageHeader, Section, Skeleton, Stat, StatGrid } from "@/ui";

interface Move { short: string; lastWeekPrice: number; priceNow: number; delta: number }
interface Row { clientId: string; clientName: string; type?: string; salesRep?: string; orders60d: number; announced: boolean; announcedAt?: string; moves: Move[]; sensitive: boolean }
interface Board { weekOf: string; today: string; clients: Row[]; told: number; total: number }

const fetchBoard = async (): Promise<Board> => {
  const res = await fetch(`${API_BASE}/cotation/board`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
};

const euro = (n: number) => n.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const cents = (d: number) => `${d > 0 ? "+" : "−"}${Math.round(Math.abs(d) * 100)} c`;

export default function CotationPage() {
  const { data, isError, refetch } = useQuery({ queryKey: ["cotation", "board"], queryFn: fetchBoard });
  const onActivity = useCallback((ev: ActivityEvent) => { if (ev.type.startsWith("cotation.")) void refetch(); }, [refetch]);
  useOnActivity(onActivity);
  const todo = data?.clients.filter((c) => !c.announced) ?? [];
  const done = data?.clients.filter((c) => c.announced) ?? [];

  return (
    <Page>
      <PageHeader title="Cotation de la semaine" icon={<TrendingUp size={16} strokeWidth={1.75} />} />
      <PageBody>
        {isError && !data ? (
          <ErrorState message="Le tableau de la cotation ne répond pas (GET /api/cotation/board)." onRetry={() => refetch()} />
        ) : !data ? (
          <Skeleton className="h-[320px] w-full rounded-[6px]" />
        ) : (
          <div className="space-y-6">
            <StatGrid>
              <Stat icon={CheckCircle2} label="Bouchers prévenus cette semaine" value={`${data.told} / ${data.total}`} tone={data.told === data.total ? "success" : undefined} hint={`semaine du ${data.weekOf.slice(8)}/${data.weekOf.slice(5, 7)} · l'agent vocal prévient pendant l'appel`} />
              <Stat icon={BellRing} label="À prévenir" value={todo.length} tone={todo.some((c) => c.sensitive) ? "warning" : undefined} hint={`dont ${todo.filter((c) => c.sensitive).length} que les hausses non annoncées agacent (fiche client)`} />
            </StatGrid>
            <Section title="À prévenir" count={todo.length}><Rows rows={todo} /></Section>
            <Section title="Déjà prévenus" count={done.length}><Rows rows={done} /></Section>
          </div>
        )}
      </PageBody>
    </Page>
  );
}

function Rows({ rows }: { rows: Row[] }) {
  if (!rows.length) return <p className="text-[12.5px] text-muted-foreground">Personne.</p>;
  return (
    <Card className="divide-y divide-border">
      {rows.map((r) => (
        <div key={r.clientId} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-[13px]">
          <Link to={`/clients/${r.clientId}`} className="min-w-[200px] font-medium hover:underline">{r.clientName}</Link>
          {r.sensitive ? <Badge tone="warning">n'aime pas les hausses non annoncées</Badge> : null}
          <span className="flex flex-wrap gap-3 text-muted-foreground">
            {r.moves.length ? r.moves.slice(0, 3).map((m) => (
              <span key={m.short}>{m.short} <span className="num text-foreground">{euro(m.priceNow)}</span> <span className={m.delta > 0 ? "num text-warning" : "num text-success"}>{cents(m.delta)}</span></span>
            )) : <span>pas de variation</span>}
          </span>
          <span className="ml-auto text-muted-foreground">{r.announced && r.announcedAt ? <>prévenu <DateLabel date={r.announcedAt} format="relative" /></> : r.salesRep ?? ""}</span>
        </div>
      ))}
    </Card>
  );
}
