/**
 * Call cards (right column of the Voix page, above "ERP en direct"):
 *  - Client en ligne: who is calling, as soon as the agent knows (identify_caller result, or any tool called with a clientId).
 *  - Commande en cours: the order being written during the call, line by line, with a stock badge for the delivery date.
 *    Removed lines stay visible, crossed out; changed quantities show the old one crossed out. Under them, in red, what
 *    the business rules refused during the call and why (out of stock, ordered too late, blocked account), read from
 *    the tools' results: the jury sees the rule applied, not just a sentence they might miss.
 *  - Suggestions: what suggest_items found at the end of the order (dot + word for the reason, then the evidence).
 *    The states are inferred, not reported: "proposé" once the agent's words name the product, accepted when it is in
 *    the order (it then moves into the order card), "non retenu" once the next one is offered or the order confirmed.
 *
 * Sources: the agent's tool calls of this session (args, and `result` when the AI service forwards it) and the live ERP
 * events written by the voice agent since the session started. Nothing here writes to the ERP.
 */
import { useMemo, useRef, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Ban, Lightbulb, Phone, Repeat, ShoppingCart } from "lucide-react";
import type { ActivityEvent, ClientDetail, Id, OrderDetail, StockAvailability } from "@kit/shared";
import type { VoiceTurn } from "@/features/assistant/useVoiceSession";
import { cn } from "@/lib/cn";
import { entityPath } from "@/lib/links";
import { WEEKDAY_LABEL, WEEKDAYS } from "@/lib/labels";
import { useClient, useEvents, useOrder, useProduct, useStockAvailability } from "@/lib/queries";
import { Badge, DateLabel, Money, Qty, SECTION_LABEL, Skeleton, StatusDot, type Tone } from "@/ui";

type Obj = Record<string, unknown>;
const isObj = (x: unknown): x is Obj => !!x && typeof x === "object" && !Array.isArray(x);
const str = (x: unknown) => (typeof x === "string" && x ? x : undefined);

interface Candidate { id: Id; name: string; city?: string }

/** Something the business rules refused during the call (the tool wrote nothing), with the reason as the tool gave it. */
export interface Refusal {
  key: string;
  productId?: Id;
  product?: string;
  qty?: number;
  unit?: string;
  reason: string;
  date?: string; // delivery date asked, YYYY-MM-DD
  day?: string; // "mercredi 25"
}

/** One product suggest_items found (tools/suggest.py), with where it came from. */
export interface Suggestion {
  productId: Id;
  name: string;
  qty: number;
  unit: string;
  kind: string; // "habitude" | "l'an dernier" | "lot à écouler" | "promo" | "réservation"
  evidence: string;
}

interface CallState {
  clientId?: Id;
  candidates: Candidate[];
  orderId?: Id;
  refusals: Refusal[];
  suggestions: Suggestion[];
  suggestedAt?: number; // index of the turn where suggest_items ran
}

const ORDER_TOOLS = new Set(["create_draft_order", "add_order_line", "update_order_line", "update_order", "confirm_order"]);
const num = (x: unknown) => (typeof x === "number" && Number.isFinite(x) ? x : undefined);
const fr = (n: number) => String(Math.round(n * 10) / 10).replace(".", ",");

/** "Trop tard pour cette date : ce produit se commande 2 jours avant. Première livraison possible : samedi 28 (2026-11-28)."
 *  → "se commande 2 jours avant → samedi 28" */
export function shortLeadTime(text: string): string {
  return text
    .replace(/^Trop tard pour cette date\s*:\s*/i, "")
    .replace(/^ce produit /i, "")
    .replace(/\.?\s*Première livraison possible\s*:\s*([^(.]+?)\s*(\(\d{4}-\d{2}-\d{2}\))?\.?$/i, " → $1")
    .trim();
}

/** What one tool result says was refused. Reads the tools' own words (tools/desk.py problems_of, tools/orders.py). */
export function refusalsOf(name: string, ok: boolean | undefined, result: unknown): Refusal[] {
  if (!isObj(result)) return [];
  const err = str(result.error);
  if (ok === false && err && /compte bloqué/i.test(err) && ORDER_TOOLS.has(name)) {
    return [{ key: "blocked", reason: "Compte bloqué : aucune commande tant que la comptabilité n'a pas levé le blocage" }];
  }
  const refusedWrite = result.written === false && Array.isArray(result.problems);
  if (!refusedWrite && name !== "check_products") return [];
  const date = str(result.deliveryDate);
  const day = str(result.jour);
  const out: Refusal[] = [];
  if (refusedWrite && str(result.deliveryDay)) out.push({ key: `day:${date}`, reason: String(result.deliveryDay), date, day });
  for (const row of Array.isArray(result.items) ? result.items.filter(isObj) : []) {
    const reasons: string[] = [];
    const unit = str(row.unit);
    if (row.stock === "rupture") reasons.push("rupture");
    else if (row.stock === "insuffisant") reasons.push(`stock insuffisant (${fr(num(row.availableQty) ?? 0)} ${unit ?? ""} possibles)`.replace(" )", ")"));
    if (reasons.length) {
      const next = row.nextArrival;
      if (isObj(next) && str(next.jour)) reasons.push(`prochain arrivage ${next.jour}`);
      else if (typeof next === "string" && next) reasons.push(next);
    }
    if (str(row.leadTime)) reasons.push(shortLeadTime(String(row.leadTime)));
    if (!reasons.length) continue;
    const productId = str(row.productId);
    out.push({ key: `${productId}:${date}`, productId, product: str(row.name), qty: num(row.qty), unit, reason: reasons.join(" · "), date, day });
  }
  return out;
}

/** Walk the session's tool runs (oldest first): the latest client / order the agent worked on wins. */
function fromTools(turns: VoiceTurn[]): CallState {
  const s: CallState = { candidates: [], refusals: [], suggestions: [] };
  const refused = new Map<string, Refusal>();
  for (const [i, turn] of turns.entries()) {
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
      for (const x of refusalsOf(t.name, t.ok, t.result)) { refused.delete(x.key); refused.set(x.key, x); } // latest reason wins
      if (t.name === "suggest_items" && t.ok && r && Array.isArray(r.suggestions)) {
        s.suggestions = r.suggestions.filter(isObj).flatMap((x) => (str(x.productId) && num(x.qty) != null ? [{
          productId: x.productId as Id, name: String(x.name ?? x.productId), qty: num(x.qty)!, unit: String(x.unit ?? ""),
          kind: String(x.reasonKind ?? ""), evidence: String(x.evidence ?? ""),
        }] : []));
        s.suggestedAt = i;
      }
    }
  }
  s.refusals = [...refused.values()];
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
  const offers = useMemo(() => suggestionStates(tools, turns, order), [tools, turns, order]);
  const accepted = useMemo(() => new Map(offers.filter((o) => o.state === "accepted").map((o) => [o.s.productId, o.s])), [offers]);

  return (
    <div className="flex flex-col">
      <ClientCard clientId={clientId} candidates={tools.candidates} />
      <OrderCard orderId={orderId} order={order} session={since} refusals={tools.refusals} accepted={accepted} />
      <SuggestionList offers={offers.filter((o) => o.state !== "accepted")} />
    </div>
  );
}

// ───────────────────────── Client en ligne ─────────────────────────

/** The sentence of the preferences that talks about substitutions, and whether it is a refusal. */
function substitutionRule(prefs: string | undefined): { label: string; rest: string; refuses: boolean } | undefined {
  const sentence = (prefs ?? "").split(/(?<=\.)\s+/).find((s) => /substitu/i.test(s))?.trim();
  if (!sentence) return undefined;
  const refuses = /(refuse|aucune|jamais|sans l'appeler|appeler avant)/i.test(sentence);
  const label = refuses ? "Refuse les substitutions" : "Substitutions";
  // "Refuse les substitutions : appeler avant…" → label + "appeler avant…" (the label is not repeated).
  const rest = sentence.toLowerCase().startsWith(label.toLowerCase()) ? sentence.slice(label.length).replace(/^[\s:·,-]+/, "") : sentence;
  return { label, rest: rest ? rest[0].toUpperCase() + rest.slice(1) : "", refuses };
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
          <span className={cn("font-semibold", sub.refuses ? "text-destructive" : "text-foreground")}>{sub.label}</span>
          {sub.rest ? <span className="text-muted-foreground"> · {sub.rest}</span> : null}
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

/** A line is identified by its id AND its product: the agent may swap the product on an existing line ("enlève le
 *  paleron, mets plutôt de la tende" → same lineId, new productId). The old product must then show crossed out. */
const lineKey = (l: Line) => `${l.id}:${l.productId}`;

interface Memory {
  /** Which order this memory is about: its id, when it was created, and the call (session start). After `make reset`
   *  the ERP hands out the same order id again (ord_020821 = CMD-2026-006259) for another order, so the id alone
   *  would mix the lines of several test calls. */
  key?: string;
  initial: Set<string>; // line keys already there when the card first saw the order (no flash)
  lines: Map<string, Line>; // every line key seen during the call, in first-seen order
  firstQty: Map<string, number>;
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

function OrderCard({ orderId, order, session, refusals: all, accepted }: { orderId?: Id; order?: OrderDetail; session: string; refusals: Refusal[]; accepted: Map<Id, Suggestion> }) {
  const mem = useRef<Memory>({ initial: new Set(), lines: new Map(), firstQty: new Map() });
  const memKey = order ? `${order.id}|${order.createdAt}|${session}` : undefined;
  if (order && mem.current.key !== memKey) {
    mem.current = { key: memKey, initial: new Set(order.lines.map(lineKey)), lines: new Map(), firstQty: new Map() };
  }
  const m = mem.current;
  if (order) for (const l of order.lines) { const k = lineKey(l); m.lines.set(k, l); if (!m.firstQty.has(k)) m.firstQty.set(k, l.qty); }

  const ids = useMemo(() => [...new Set(order?.lines.map((l) => l.productId) ?? [])].sort(), [order]);
  const { data: avail } = useStockAvailability(order?.deliveryDate, ids);
  const rows = useMemo(() => new Map((avail ?? []).map((r) => [r.productId, r])), [avail]);

  const current = new Set(order?.lines.map(lineKey));
  // The order as it stands first (in the ERP's order), then what was taken off during the call, crossed out.
  const shown = [...(order?.lines ?? []), ...[...m.lines.values()].filter((l) => !current.has(lineKey(l)))];
  // A refusal the call got past (the product is in the order for that date after all, e.g. a smaller quantity) is
  // no longer news. The blocked account always stays.
  const refusals = all.filter((x) => !(x.productId && order && x.date === order.deliveryDate && order.lines.some((l) => l.productId === x.productId)));

  return (
    <section className="border-b border-border">
      <CardHeader
        icon={ShoppingCart}
        title="Commande en cours"
        right={order ? <StatusDot kind="order" value={order.status} /> : null}
      />
      {!orderId ? (
        refusals.length ? null : <div className="px-4 py-3 text-[12.5px] text-muted-foreground">Aucune commande pour l'instant : les lignes s'écrivent ici pendant l'appel.</div>
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
                const k = lineKey(l);
                const removed = !current.has(k) || order.status === "cancelled";
                const first = m.firstQty.get(k);
                const changed = !removed && first != null && first !== l.qty;
                const st = removed ? undefined : stockState(l, order, rows);
                return (
                  <li key={k} className={cn("flex items-center gap-2 px-4 py-1", !m.initial.has(k) && "animate-flash")}>
                    <span className="min-w-0 flex-1">
                      <span className={cn("block truncate", removed && "text-muted-foreground line-through")} title={l.productName}>{l.productName}</span>
                      {l.substituteFor && !removed ? <Replaces productId={l.substituteFor} /> : null}
                      {!removed && accepted.has(l.productId) ? <AcceptedSuggestion s={accepted.get(l.productId)!} /> : null}
                    </span>
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
      {refusals.length ? <RefusalList refusals={refusals} showDay={!order || refusals.some((x) => x.date && x.date !== order.deliveryDate)} /> : null}
    </section>
  );
}

/** "Refusé pendant l'appel": one red line per product the rules refused, with the tool's reason. */
function RefusalList({ refusals, showDay }: { refusals: Refusal[]; showDay: boolean }) {
  return (
    <div className="border-t border-destructive/20 bg-destructive/[.05] px-4 py-2 text-[12px]">
      <div className={cn(SECTION_LABEL, "mb-1 flex items-center gap-1.5 text-destructive")}><Ban size={11} strokeWidth={2} />Refusé pendant l'appel</div>
      <ul className="flex flex-col gap-1">
        {refusals.map((x) => (
          <li key={x.key} className="animate-flash leading-[16px]">
            {x.product ? (
              <span className="font-medium">
                {x.product}
                {x.qty != null ? <span className="num font-normal text-muted-foreground"> · {fr(x.qty)} {x.unit}</span> : null}
                {showDay && x.day ? <span className="font-normal text-muted-foreground"> · pour {x.day}</span> : null}
              </span>
            ) : null}
            <span className="block text-destructive">{x.reason}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Under a substitute line: which product the client accepted it in place of ("remplace Onglet de bœuf"). */
function Replaces({ productId }: { productId: Id }) {
  const name = useProduct(productId).data?.name;
  return (
    <span className="flex items-center gap-1 text-[11px] text-success">
      <Repeat size={10} strokeWidth={2} className="shrink-0" />
      <span className="truncate">remplace {name ?? productId}</span>
    </span>
  );
}

// ───────────────────────── Suggestions ─────────────────────────

/** Dot colour per reason, from the existing tones (no new colour). */
const KIND_TONE: Record<string, Tone> = {
  "l'an dernier": "violet",
  "habitude": "info",
  "promo": "success",
  "lot à écouler": "warning",
};
const GENERIC = new Set(["demi", "carcasse", "boeuf", "limousin", "label", "rouge", "genisse", "sous", "mere", "frais", "fraiche", "facon", "entier", "entiere", "pour", "avec"]);
const fold = (t: string) => t.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
const words = (name: string) => fold(name).split(/[^a-z0-9]+/).filter((w) => w.length >= 4 && !GENERIC.has(w));

type OfferState = "proposed" | "accepted" | "declined";
interface Offer { s: Suggestion; state: OfferState }

/** Which suggestions the agent has offered so far, and what became of each (inferred: see the header comment). */
function suggestionStates(tools: CallState, turns: VoiceTurn[], order: OrderDetail | undefined): Offer[] {
  const list = tools.suggestions;
  if (!list.length || tools.suggestedAt == null) return [];
  const inOrder = new Set(order?.lines.map((l) => l.productId) ?? []);
  // the words that tell a suggestion apart from the other suggestions and from the order's lines ("porc", "avant")
  const others = (i: number) => new Set([...list.filter((_, j) => j !== i).map((x) => x.name), ...(order?.lines.map((l) => l.productName) ?? [])].flatMap(words));
  const keys = list.map((x, i) => { const own = words(x.name); const k = own.filter((w) => !others(i).has(w)); return k.length ? k : own; });
  const said = fold(turns.slice(tools.suggestedAt).map((t) => t.agent.text).join(" "));
  let reached = -1;
  keys.forEach((k, i) => { if (k.some((w) => said.includes(w))) reached = i; });
  if (reached < 0 && said.trim()) reached = 0; // the agent spoke after the tool: the first one is on the table
  const ended = !!order && order.status !== "draft";
  return list.slice(0, reached + 1).map((s, i) => ({
    s,
    state: inOrder.has(s.productId) ? "accepted" : i < reached || ended ? "declined" : "proposed",
  }));
}

function KindTag({ kind }: { kind: string }) {
  return <StatusDot tone={KIND_TONE[kind] ?? "muted"} label={kind} className="text-[11px]" />;
}

/** "Suggestions": what the agent offered at the end of the order, and why (accepted ones are in the order card). */
function SuggestionList({ offers }: { offers: Offer[] }) {
  if (!offers.length) return null;
  return (
    <section className="border-b border-border py-2 text-[12px]">
      <div className={cn(SECTION_LABEL, "mb-1 flex items-center gap-1.5 px-4")}><Lightbulb size={11} strokeWidth={2} />Suggestions</div>
      <ul className="flex flex-col gap-1.5">
        {offers.map(({ s, state }) => (
          <li key={s.productId} className={cn("animate-flash px-4 leading-[16px]", state === "declined" && "opacity-55")}>
            <div className="flex items-center gap-2">
              <span className="min-w-0 flex-1 truncate font-medium" title={s.name}>{s.name}</span>
              <Qty value={s.qty} unit={s.unit} className="shrink-0 text-[12px]" />
              <span className="w-[74px] shrink-0 text-right">
                {state === "declined" ? <Badge>Non retenu</Badge> : <Badge tone="violet">Proposé</Badge>}
              </span>
            </div>
            <div className="flex min-w-0 items-center gap-2 text-muted-foreground">
              <KindTag kind={s.kind} />
              <span className="truncate text-[11px]" title={s.evidence}>{s.evidence}</span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Under an order line the client took on the agent's suggestion. */
function AcceptedSuggestion({ s }: { s: Suggestion }) {
  return (
    <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
      <span>suggestion acceptée</span>
      <KindTag kind={s.kind} />
    </span>
  );
}
