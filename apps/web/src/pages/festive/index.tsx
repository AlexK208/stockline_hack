/** Carnet des fêtes — Christmas / New Year reservations taken by phone (GET /api/festive/board). Live: refetches on
 *  every festive.* activity event, so a reservation made by the voice agent fills its bar while the caller is talking. */
import { useCallback } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Gift, Hourglass, MessageSquareQuote, PackageCheck } from "lucide-react";
import type { ActivityEvent } from "@kit/shared";
import { API_BASE } from "@/lib/api";
import { useOnActivity } from "@/lib/queries";
import { useUrlState } from "@/lib/url-state";
import {
  ActorIcon, Badge, Card, DateLabel, EmptyState, ErrorState, Page, PageBody, PageHeader, Qty, Section, Skeleton, Stat, StatGrid, Tabs,
} from "@/ui";

interface BoardClient { clientId: string; clientName?: string; qtyReserved: number; qtyWaitlist: number; deliveryDate: string; reservationId: string; createdBy?: string }
interface ScarcePiece { productId: string; productName: string; unit?: string; reason: string; capacity: number; reserved: number; waitlist: number; left: number; shortfall: number; clients: BoardClient[] }
interface OtherPiece { productId: string; productName: string; unit?: string; reserved: number }
interface BoardWindow { window: "noel" | "nouvel_an"; label: string; dates: [string, string]; scarce: ScarcePiece[]; other: OtherPiece[] }
interface PendingRequest { eventId: string; clientId: string; clientName?: string; at: string; title: string; description?: string }
interface Board { today: string; windows: BoardWindow[]; pendingRequests: PendingRequest[] }

const fetchBoard = async (): Promise<Board> => {
  const res = await fetch(`${API_BASE}/festive/board`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
};

export default function FestivePage() {
  const { data, isError, refetch } = useQuery({ queryKey: ["festive", "board"], queryFn: fetchBoard });
  const onActivity = useCallback((ev: ActivityEvent) => { if (ev.type.startsWith("festive.")) void refetch(); }, [refetch]);
  useOnActivity(onActivity);
  const [tab, setTab] = useUrlState("window", "noel");
  const win = data?.windows.find((w) => w.window === tab) ?? data?.windows[0];

  const booked = win?.scarce.filter((p) => p.reserved > 0).length ?? 0;
  const waiting = win?.scarce.reduce((n, p) => n + p.clients.filter((c) => c.qtyWaitlist > 0).length, 0) ?? 0;
  const short = win?.scarce.filter((p) => p.shortfall > 0) ?? [];

  return (
    <Page>
      <PageHeader
        title="Carnet des fêtes"
        icon={<Gift size={16} strokeWidth={1.75} />}
        tabs={data ? <Tabs value={win?.window ?? "noel"} onChange={setTab} items={data.windows.map((w) => ({ id: w.window, label: `${w.label} · ${w.dates[0].slice(8)}–${w.dates[1].slice(8)}/12` }))} /> : undefined}
      />
      <PageBody>
        {isError && !data ? (
          <ErrorState message="Le carnet des fêtes ne répond pas (GET /api/festive/board)." onRetry={() => refetch()} />
        ) : !data || !win ? (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 2xl:grid-cols-3">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-[180px] w-full rounded-[6px]" />)}</div>
        ) : (
          <div className="space-y-6">
            <StatGrid>
              <Stat icon={PackageCheck} label="Pièces limitées réservées" value={`${booked} / ${win.scarce.length}`} hint="capacité = le maximum livré l'an dernier sur ces dates" />
              <Stat icon={Hourglass} label="Clients en liste d'attente" value={waiting} tone={waiting ? "warning" : undefined} hint={short.length ? `à trouver : ${short.map((p) => `${fmt(p.shortfall)} ${p.unit ?? ""} ${shortName(p.productName)}`).join(", ")}` : "rien à trouver pour l'instant"} />
              <Stat icon={MessageSquareQuote} label="Demandes encore en texte" value={data.pendingRequests.length} hint="clients qui ont parlé des fêtes sans réservation chiffrée" />
            </StatGrid>

            <Section title="Pièces limitées" count={win.scarce.length}>
              <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2 2xl:grid-cols-3">
                {win.scarce.map((p) => <PieceCard key={p.productId} p={p} />)}
              </div>
            </Section>

            <Section title="Autres pièces réservées (sans plafond)" count={win.other.length}>
              {win.other.length === 0 ? (
                <p className="text-[12.5px] text-muted-foreground">Aucune pour l'instant.</p>
              ) : (
                <Card className="divide-y divide-border">
                  {win.other.map((o) => (
                    <div key={o.productId} className="flex items-center justify-between px-3 py-2 text-[13px]">
                      <span>{o.productName}</span><Qty value={o.reserved} unit={o.unit} />
                    </div>
                  ))}
                </Card>
              )}
            </Section>

            <Section title="Demandes des fêtes restées en texte" count={data.pendingRequests.length}>
              {data.pendingRequests.length === 0 ? (
                <EmptyState compact icon={MessageSquareQuote} title="Tout est chiffré" description="Chaque client qui a parlé des fêtes a une réservation." />
              ) : (
                <Card className="divide-y divide-border">
                  {data.pendingRequests.map((r) => (
                    <div key={r.eventId} className="flex items-start gap-3 px-3 py-2 text-[13px]">
                      <DateLabel date={r.at} className="w-[72px] shrink-0 text-muted-foreground" />
                      <div className="min-w-0">
                        <Link to={`/clients/${r.clientId}`} className="font-medium hover:underline">{r.clientName ?? r.clientId}</Link>
                        <p className="line-clamp-2 text-muted-foreground">{r.description ?? r.title}</p>
                      </div>
                    </div>
                  ))}
                </Card>
              )}
            </Section>
          </div>
        )}
      </PageBody>
    </Page>
  );
}

function PieceCard({ p }: { p: ScarcePiece }) {
  const cap = p.capacity || 1;
  const reservedPct = Math.min(100, (p.reserved / cap) * 100);
  const waitPct = Math.min(100 - reservedPct, (p.waitlist / cap) * 100);
  return (
    <Card className="p-3">
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-medium">{p.productName}</span>
        {p.shortfall > 0 ? <Badge tone="warning">manque {fmt(p.shortfall)} {p.unit}</Badge> : p.left === 0 && p.reserved > 0 ? <Badge tone="destructive">complet</Badge> : null}
      </div>
      <p className="mt-0.5 text-[12px] text-muted-foreground">{p.reason}</p>
      <div className="mt-3 flex h-2 w-full overflow-hidden rounded-full bg-muted" aria-label={`${fmt(p.reserved)} réservés sur ${fmt(p.capacity)}`}>
        <div className="h-full bg-success transition-all duration-500" style={{ width: `${reservedPct}%` }} />
        <div className="h-full bg-warning transition-all duration-500" style={{ width: `${waitPct}%` }} />
      </div>
      <div className="mt-1.5 flex justify-between text-[12px] text-muted-foreground">
        <span><span className="num text-foreground">{fmt(p.reserved)}</span> réservés{p.waitlist ? <> · <span className="num text-warning">{fmt(p.waitlist)}</span> en attente</> : null}</span>
        <span>capacité <span className="num">{fmt(p.capacity)}</span> {p.unit}</span>
      </div>
      {p.clients.length ? (
        <ul className="mt-2 space-y-1 border-t border-border pt-2 text-[12.5px]">
          {p.clients.map((c) => (
            <li key={c.reservationId} className="flex items-center gap-2">
              <Link to={`/clients/${c.clientId}`} className="min-w-0 truncate hover:underline">{c.clientName ?? c.clientId}</Link>
              {c.createdBy ? <ActorIcon actor={c.createdBy as ActivityEvent["actor"]} size={16} /> : null}
              <span className="ml-auto num">{fmt(c.qtyReserved)}</span>
              {c.qtyWaitlist ? <span className="num text-warning">+{fmt(c.qtyWaitlist)}</span> : null}
              <span className="text-muted-foreground">{c.deliveryDate.slice(8)}/12</span>
            </li>
          ))}
        </ul>
      ) : null}
    </Card>
  );
}

const fmt = (n: number) => n.toLocaleString("fr-FR", { maximumFractionDigits: 1 });
const shortName = (name: string) => name.split(/\s(?:de|du|sous|limousin|\()/)[0].toLowerCase();
