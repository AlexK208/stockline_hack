/**
 * Call cards (right column of the Voix page, above "ERP en direct"):
 *  - Client en ligne: who is calling, as soon as the agent knows (identify_caller result, or any tool called with a clientId).
 *  - Commande en cours: the order being written during the call, line by line, with a stock badge for the delivery date.
 *    Removed lines stay visible, crossed out; changed quantities show the old one crossed out.
 *
 * Sources: the agent's tool calls of this session (args, and `result` when the AI service forwards it) and the live ERP
 * events written by the voice agent since the session started. Nothing here writes to the ERP.
 */
import { useMemo, useRef, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Phone, ShoppingCart } from "lucide-react";
import type { ActivityEvent, ClientDetail, Id, OrderDetail, StockAvailability } from "@kit/shared";
import type { VoiceTurn } from "@/features/assistant/useVoiceSession";
import { cn } from "@/lib/cn";
import { entityPath } from "@/lib/links";
import { WEEKDAY_LABEL, WEEKDAYS } from "@/lib/labels";
import { useClient, useEvents, useOrder, useStockAvailability } from "@/lib/queries";
import { Badge, DateLabel, Money, Qty, SECTION_LABEL, Skeleton, StatusDot } from "@/ui";

type Obj = Record<string, unknown>;
const isObj = (x: unknown): x is Obj => !!x && typeof x === "object" && !Array.isArray(x);
const str = (x: unknown) => (typeof x === "string" && x ? x : undefined);

interface Candidate { id: Id; name: string; city?: string }

interface CallState {
  clientId?: Id;
  candidates: Candidate[];
  orderId?: Id;
}

/** Walk the session's tool runs (oldest first): the latest client / order the agent worked on wins. */
function fromTools(turns: VoiceTurn[]): CallState {
  const s: CallState = { candidates: [] };
  for (const turn of turns) {
    for (const t of turn.agent.tools) {
      const a = t.args ?? {};
      const r = isObj(t.result) ? t.result : undefined;
      const argClient = str(a.clientId);
      if (argClient) { s.clientId = argClient; s.candidates = []; }
      if (t.name === "identify_caller" && r) {
        if (r.status === "found" && isObj(r.client) && str(r.client.id)) { s.clientId = str(r.client.id); s.candidates = []; }
        else if (r.status === "ambiguous" && Array.isArray(r.candidates)) {
          s.candidates = r.candidates.filter(isObj).flatMap((c) => (str(c.id) ? [{ id: c.id as Id, name: String(c.name ?? c.id), city: str(c.city) }] : []));
        }
      }
      const argOrder = str(a.orderId);
      if (argOrder) s.orderId = argOrder;
      if (r && t.ok && str(r.id) && typeof r.number === "string" && Array.isArray(r.lines)) s.orderId = r.id as Id;
    }
  }
  return s;
}

/** Latest order written by the voice agent since `since` (business clock, like the events). */
function latestVoiceOrder(events: ActivityEvent[] | undefined, since: string): Id | undefined {
  return events?.find((e) => e.actor === "voice_agent" && e.entity === "order" && e.at >= since)?.entityId;
}

export function CallCards({ turns, since }: { turns: VoiceTurn[]; since: string }) {
  const { data: events } = useEvents(200);
  const tools = useMemo(() => fromTools(turns), [turns]);
  const eventOrder = latestVoiceOrder(events, since);
  const orderId = eventOrder ?? tools.orderId;
  const order = useOrder(orderId).data;
  const clientId = tools.clientId ?? order?.clientId;

  return (
    <div className="flex flex-col">
      <ClientCard clientId={clientId} candidates={tools.candidates} />
      <OrderCard orderId={orderId} order={order} />
    </div>
  );
}

// ───────────────────────── Client en ligne ─────────────────────────

/** The sentence of the preferences that talks about substitutions, and whether it is a refusal. */
function substitutionRule(prefs: string | undefined): { text: string; refuses: boolean } | undefined {
  const sentence = (prefs ?? "").split(/(?<=\.)\s+/).find((s) => /substitu/i.test(s));
  if (!sentence) return undefined;
  return { text: sentence.trim(), refuses: /(refuse|aucune|jamais|sans l'appeler|appeler avant)/i.test(sentence) };
}

function CardHeader({ icon: Icon, title, right }: { icon: typeof Phone; title: string; right?: ReactNode }) {
  return (
    <div className="flex h-10 shrink-0 items-center gap-2 border-b border-border px-4">
      <Icon size={13} strokeWidth={1.75} className="text-violet" />
      <span className={SECTION_LABEL}>{title}</span>
      <span className="ml-auto flex items-center gap-1.5">{right}</span>
    </div>
  );
}

function ClientCard({ clientId, candidates }: { clientId?: Id; candidates: Candidate[] }) {
  const { data: c, isLoading } = useClient(clientId);

  let body: ReactNode;
  if (!clientId && candidates.length) {
    body = (
      <div className="px-4 py-3 text-[12.5px]">
        <div className="mb-1.5 text-muted-foreground">Plusieurs clients possibles, l'agent demande lequel :</div>
        <ul className="flex flex-col gap-1">
          {candidates.map((k) => (
            <li key={k.id} className="flex items-center gap-1.5"><span className="font-medium">{k.name}</span>{k.city ? <span className="text-muted-foreground">· {k.city}</span> : null}</li>
          ))}
        </ul>
      </div>
    );
  } else if (!clientId) {
    body = <div className="px-4 py-3 text-[12.5px] text-muted-foreground">En attente : le client apparaît dès que l'agent l'identifie.</div>;
  } else if (isLoading || !c) {
    body = <div className="flex flex-col gap-1.5 px-4 py-3"><Skeleton className="h-4 w-[70%]" /><Skeleton className="h-3 w-[50%]" /><Skeleton className="h-3 w-[80%]" /></div>;
  } else {
    body = <ClientBody c={c} />;
  }

  return (
    <section className="border-b border-border">
      <CardHeader
        icon={Phone}
        title="Client en ligne"
        right={c && clientId ? (c.status === "blocked" ? <Badge tone="destructive">Compte bloqué</Badge> : <Badge tone="success">Compte OK</Badge>) : null}
      />
      {body}
    </section>
  );
}

function ClientBody({ c }: { c: ClientDetail }) {
  const sub = substitutionRule(c.preferences);
  const days = WEEKDAYS.filter((d) => c.deliveryDays.includes(d)).map((d) => WEEKDAY_LABEL[d]).join(" ");
  const usual = [...(c.usual ?? [])].sort((a, b) => b.frequency - a.frequency).slice(0, 5);
  return (
    <div key={c.id} className="flex animate-flash flex-col gap-2 px-4 py-3 text-[12.5px]">
      <div>
        <Link to={entityPath("client", c.id) ?? "#"} className="group inline-flex items-center gap-1 text-[14px] font-semibold leading-tight hover:underline">
          {c.name}<ArrowUpRight size={12} className="text-muted-foreground group-hover:text-foreground" />
        </Link>
        <div className="text-[11.5px] text-muted-foreground">{c.city} · {c.code}</div>
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[12px]">
        <dt className="text-muted-foreground">Commercial</dt><dd>{c.salesRep}</dd>
        <dt className="text-muted-foreground">Livré</dt><dd>{days || "—"}</dd>
        {c.overdue > 0 ? (<><dt className="text-muted-foreground">Retard</dt><dd><Money value={c.overdue} tone="destructive" /></dd></>) : null}
      </dl>
      {sub ? (
        <div className={cn("rounded-[3px] border px-2 py-1.5 text-[11.5px] leading-[15px]", sub.refuses ? "border-destructive/25 bg-destructive/[.06]" : "border-border bg-muted/50")}>
          <span className={cn("font-semibold", sub.refuses ? "text-destructive" : "text-foreground")}>{sub.refuses ? "Refuse les substitutions" : "Substitutions"}</span>
          <span className="text-muted-foreground"> · {sub.text}</span>
        </div>
      ) : null}
      {usual.length ? (
        <div>
          <div className={cn(SECTION_LABEL, "mb-1")}>Sa commande habituelle</div>
          <ul className="flex flex-col gap-0.5">
            {usual.map((u) => (
              <li key={u.productId} className="flex items-baseline justify-between gap-2">
                <span className="truncate">{u.productName}</span>
                <Qty value={Math.round(u.avgQty * 10) / 10} unit={u.unit} className="shrink-0 text-[12px]" />
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

// ───────────────────────── Commande en cours ─────────────────────────

type Line = OrderDetail["lines"][number];

interface Memory {
  orderId?: Id;
  initial: Set<Id>; // lines already there when the card first saw the order (no flash)
  lines: Map<Id, Line>; // every line seen during the call, in first-seen order
  firstQty: Map<Id, number>;
}

function stockState(line: Line, order: OrderDetail, rows: Map<Id, StockAvailability>): "ok" | "short" | "out" | undefined {
  const r = rows.get(line.productId);
  if (!r) return undefined;
  // A confirmed order already reserves its own lines in availableOn; a draft does not.
  const left = order.status === "draft" ? r.availableOn - line.qty : r.availableOn;
  if (left >= -1e-9) return "ok";
  const before = order.status === "draft" ? r.availableOn : r.availableOn + line.qty;
  return before <= 0 ? "out" : "short";
}

function OrderCard({ orderId, order }: { orderId?: Id; order?: OrderDetail }) {
  const mem = useRef<Memory>({ initial: new Set(), lines: new Map(), firstQty: new Map() });
  if (order && mem.current.orderId !== order.id) {
    mem.current = { orderId: order.id, initial: new Set(order.lines.map((l) => l.id)), lines: new Map(), firstQty: new Map() };
  }
  const m = mem.current;
  if (order) for (const l of order.lines) { m.lines.set(l.id, l); if (!m.firstQty.has(l.id)) m.firstQty.set(l.id, l.qty); }

  const ids = useMemo(() => [...new Set(order?.lines.map((l) => l.productId) ?? [])].sort(), [order]);
  const { data: avail } = useStockAvailability(order?.deliveryDate, ids);
  const rows = useMemo(() => new Map((avail ?? []).map((r) => [r.productId, r])), [avail]);

  const current = new Set(order?.lines.map((l) => l.id));
  const shown = [...m.lines.values()];

  return (
    <section className="border-b border-border">
      <CardHeader
        icon={ShoppingCart}
        title="Commande en cours"
        right={order ? <StatusDot kind="order" value={order.status} /> : null}
      />
      {!orderId ? (
        <div className="px-4 py-3 text-[12.5px] text-muted-foreground">Aucune commande pour l'instant : les lignes s'écrivent ici pendant l'appel.</div>
      ) : !order ? (
        <div className="flex flex-col gap-1.5 px-4 py-3"><Skeleton className="h-3 w-[60%]" /><Skeleton className="h-3 w-[80%]" /></div>
      ) : (
        <div className="py-2 text-[12.5px]">
          <div className="flex items-baseline justify-between gap-2 px-4 pb-1.5">
            <Link to={entityPath("order", order.id) ?? "#"} className="font-mono text-[11.5px] text-muted-foreground hover:text-foreground hover:underline">{order.number}</Link>
            <span className="text-[11.5px] text-muted-foreground">Livraison <DateLabel date={order.deliveryDate} className="text-foreground" /></span>
          </div>
          {shown.length === 0 ? (
            <div className="px-4 py-1 text-muted-foreground">Pas encore de ligne.</div>
          ) : (
            <ul>
              {shown.map((l) => {
                const removed = !current.has(l.id) || order.status === "cancelled";
                const first = m.firstQty.get(l.id);
                const changed = !removed && first != null && first !== l.qty;
                const st = removed ? undefined : stockState(l, order, rows);
                return (
                  <li key={l.id} className={cn("flex items-center gap-2 px-4 py-1", !m.initial.has(l.id) && "animate-flash")}>
                    <span className={cn("min-w-0 flex-1 truncate", removed && "text-muted-foreground line-through")} title={l.productName}>{l.productName}</span>
                    <span className={cn("flex shrink-0 items-baseline gap-1", removed && "line-through opacity-60")}>
                      {changed ? <span className="num text-[11px] text-muted-foreground line-through">{first}</span> : null}
                      <Qty value={l.qty} unit={l.unit} className="text-[12px]" />
                    </span>
                    <span className="w-[62px] shrink-0 text-right">
                      {removed ? <Badge>Retirée</Badge>
                        : st === "ok" ? <Badge tone="success">En stock</Badge>
                        : st === "short" ? <Badge tone="warning">Insuffisant</Badge>
                        : st === "out" ? <Badge tone="destructive">Rupture</Badge>
                        : null}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
          <div className="mt-1 flex items-baseline justify-between border-t border-border px-4 pt-1.5">
            <span className="text-muted-foreground">Total HT estimé</span>
            <Money value={order.totalHt} className="font-semibold" />
          </div>
        </div>
      )}
    </section>
  );
}
